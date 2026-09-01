"""
Quiz Engine — deterministic unit suite (validator, scoring, shuffle, cache).

Standalone (matches repo convention): stubs env, imports pure-Python modules
that do NOT touch the network or DB, runs assertions, prints PASS/FAIL, and
exits non-zero on any failure. These cover the Phase 2 validator (§44–§46) and
the Phase 4 server-side scoring / seeded shuffle / timing (§10, §38, §41, §43,
§63) — none of which depend on the retrieval gate.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("SUPABASE_URL", "x")
os.environ.setdefault("SUPABASE_KEY", "x")
os.environ.setdefault("SUPABASE_JWT_SECRET", "x")
os.environ.setdefault("GEMINI_API_KEY", "x")
os.environ.setdefault("GROQ_API_KEY", "x")
os.environ.setdefault("CASHFREE_APP_ID", "x")
os.environ.setdefault("CASHFREE_SECRET_KEY", "x")

from datetime import datetime, timezone, timedelta
from app.services.quiz.schemas import QuizQuestion, QuestionType, QuizConfig, Difficulty
from app.services.quiz.validator import validate_questions, DUPLICATE_SIMILARITY_THRESHOLD
from app.services.quiz import scoring
from app.services.quiz.cache import compute_cache_key

_failures = []


def check(name, cond):
    if cond:
        print(f"[PASS] {name}")
    else:
        print(f"[FAIL] {name}")
        _failures.append(name)


def mcq(text, opts, ans, **kw):
    return QuizQuestion(id=kw.pop("id", text[:8]), question_text=text, type=QuestionType.MCQ,
                        options=opts, correct_answer=ans, **kw)


# ─── Validator ───────────────────────────────────────────────────────────────

def test_validator():
    good = mcq("What is 3NF in databases?", ["Third Normal Form", "Node", "Format", "None here"], "Third Normal Form")
    rep = validate_questions([good])
    check("validator accepts a well-formed mcq", rep.ok)

    bad_answer = mcq("Pick one", ["A", "B", "C"], "Z")
    rep = validate_questions([bad_answer])
    check("validator rejects answer-not-in-options",
          any(i.code == "answer_not_in_options" for i in rep.issues))

    too_few = mcq("Pick", ["A", "B"], "A")
    rep = validate_questions([too_few])
    check("validator rejects <3 mcq options", any(i.code == "too_few_options" for i in rep.issues))

    banned = mcq("Pick", ["A", "B", "All of the above"], "A")
    rep = validate_questions([banned])
    check("validator flags 'all of the above'", any(i.code == "banned_option" for i in rep.issues))

    dup_a = mcq("Which normal form eliminates transitive dependency in databases?",
                ["3NF", "1NF", "2NF", "BCNF"], "3NF", id="a")
    dup_b = mcq("Which normal form eliminates transitive dependency?",
                ["3NF", "1NF", "2NF", "BCNF"], "3NF", id="b")
    rep = validate_questions([dup_a, dup_b])
    check("validator detects near-duplicate questions (non-LLM)", len(rep.duplicate_pairs) == 1)

    empty = validate_questions([])
    check("validator flags empty quiz", any(i.code == "empty_quiz" for i in empty.issues))


# ─── Scoring (server-side, no client-trusted values) ─────────────────────────

def test_scoring():
    q1 = mcq("Q1", ["Paris", "Lyon", "Nice"], "Paris", id="q1", concept_id="geo")
    q2 = QuizQuestion(id="q2", question_text="Sky is blue?", type=QuestionType.TRUE_FALSE,
                      correct_answer="true", concept_id="sci")
    q3 = QuizQuestion(id="q3", question_text="Fill: 2+2=__", type=QuestionType.FILL_BLANK,
                      correct_answer=["4", "four"], concept_id="math")
    qs = [q1, q2, q3]

    res = scoring.score_attempt(qs, {"q1": "Paris", "q2": "true", "q3": "four"})
    check("all-correct scores 100", res["score"] == 100.0 and res["correct_count"] == 3)

    res = scoring.score_attempt(qs, {"q1": "Lyon", "q2": "false", "q3": "5"})
    check("all-wrong scores 0", res["score"] == 0.0 and res["correct_count"] == 0)

    res = scoring.score_attempt(qs, {"q1": "Paris"})
    check("unanswered questions score 0", res["correct_count"] == 1 and abs(res["score"] - 33.33) < 0.1)

    # A client cannot inject correctness: only the raw answer is graded.
    res = scoring.score_attempt(qs, {"q1": "wrong"})
    check("wrong answer stays wrong regardless of client intent", res["correct_count"] == 0)

    # concept rollup present for mastery feed
    res = scoring.score_attempt(qs, {"q1": "Paris", "q2": "true", "q3": "4"})
    check("concept_performance rolls up per concept",
          res["concept_performance"]["geo"]["accuracy"] == 1.0)

    # short-answer partial credit
    qsa = QuizQuestion(id="s1", question_text="Explain photosynthesis",
                       type=QuestionType.SHORT_ANSWER,
                       correct_answer=["plants convert sunlight into energy"])
    _, partial = scoring.grade_question(qsa, "plants use sunlight")
    check("short-answer awards partial credit", 0.0 < partial < 1.0)


# ─── Seeded shuffle reconstruction (§41, §63) ────────────────────────────────

def test_shuffle():
    ids = [f"q{i}" for i in range(10)]
    seed = 123456789
    a = scoring.shuffled_question_order(ids, seed)
    b = scoring.shuffled_question_order(ids, seed)
    check("same seed reproduces identical question order", a == b)
    check("shuffle is a permutation (no loss)", sorted(a) == sorted(ids))
    c = scoring.shuffled_question_order(ids, seed + 1)
    check("different seed generally differs", a != c)

    opts = ["A", "B", "C", "D"]
    o1 = scoring.shuffled_option_order("q1", opts, seed)
    o1b = scoring.shuffled_option_order("q1", opts, seed)
    o2 = scoring.shuffled_option_order("q2", opts, seed)
    check("option order reproducible per (seed, question)", o1 == o1b)
    check("option order independent across questions", sorted(o1) == sorted(o2) == sorted(opts))


# ─── Timing (server-enforced) ────────────────────────────────────────────────

def test_timing():
    start = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    exp = scoring.compute_expires_at(start, 300)
    check("expiry computed from server start + timer", exp == start + timedelta(seconds=300))
    check("untimed quiz has no expiry", scoring.compute_expires_at(start, None) is None)
    check("not expired before deadline", not scoring.is_expired(exp, start + timedelta(seconds=100)))
    check("expired after deadline", scoring.is_expired(exp, start + timedelta(seconds=400)))
    check("elapsed derived from timestamps",
          scoring.server_time_spent(start, start + timedelta(seconds=90)) == 90)


# ─── Cache key personalization guard (§36) ───────────────────────────────────

def test_cache_key():
    cfg = QuizConfig(question_count=10, difficulty=Difficulty.MEDIUM,
                     types=[QuestionType.MCQ], language="english")
    k1 = compute_cache_key(config=cfg, source_type="pdf", source_ids=["p1"],
                           source_versions={"p1": 1})
    k2 = compute_cache_key(config=cfg, source_type="pdf", source_ids=["p1"],
                           source_versions={"p1": 1})
    check("identical inputs -> identical cache key", k1 == k2 and k1 is not None)

    k3 = compute_cache_key(config=cfg, source_type="pdf", source_ids=["p1"],
                           source_versions={"p1": 2})
    check("source version change -> different key", k1 != k3)

    adaptive_cfg = QuizConfig(adaptive=True)
    k_adaptive = compute_cache_key(config=adaptive_cfg, source_type="pdf",
                                   source_ids=["p1"], source_versions={"p1": 1})
    check("adaptive quiz is NOT shared-cached (key is None)", k_adaptive is None)

    k_personal = compute_cache_key(config=cfg, source_type="teach_me", source_ids=[],
                                   source_versions={}, personalized=True)
    check("personalized quiz is NOT shared-cached (key is None)", k_personal is None)


# ─── Trust boundary (§10, §38, §70) ──────────────────────────────────────────

def test_trust_boundary():
    # The student-facing serialization must NEVER carry correct_answer/explanation.
    q = mcq("Capital of France?", ["Paris", "Lyon", "Nice"], "Paris", id="q1")
    q.explanation = "Paris is the capital."
    student = q.to_student_dict()
    check("student payload omits correct_answer", "correct_answer" not in student)
    check("student payload omits explanation", "explanation" not in student)

    # The submit wire model must not expose a score/is_correct field the client
    # could set — only raw answers are accepted.
    from app.models.quiz import SubmitAttemptRequest, SubmitAnswerModel
    fields = set(SubmitAnswerModel.model_fields.keys())
    check("submit answer model accepts only question_id + answer",
          fields == {"question_id", "answer"})
    top = set(SubmitAttemptRequest.model_fields.keys())
    check("submit request carries no client score field",
          "score" not in top and "is_correct" not in top)


if __name__ == "__main__":
    test_validator()
    test_scoring()
    test_shuffle()
    test_timing()
    test_cache_key()
    test_trust_boundary()
    print()
    if _failures:
        print(f"RESULT: {len(_failures)} check(s) FAILED: {_failures}")
        sys.exit(1)
    print("RESULT: all quiz-engine deterministic checks passed.")
    sys.exit(0)

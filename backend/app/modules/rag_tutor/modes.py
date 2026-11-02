"""The 10 tutor modes. Each builds its reply from verified curriculum content."""
from __future__ import annotations

import random
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from app.modules.curriculum.items import Item, get_item, items_for
from app.modules.curriculum.ncert_seed import CONCEPTS_BY_ID, Concept
from app.modules.error_to_mastery.engine import FADE_STAGES, faded_example, grade
from app.modules.rag_tutor.safety import leaks_answer

TEACH_BACK_PASS = 2


class Mode(str, Enum):
    EXPLAIN = "01_explain"
    HINT = "02_hint"
    STEP_BY_STEP = "03_step_by_step"
    SOCRATIC = "04_socratic"
    MISTAKE_REPAIR = "05_mistake_repair"
    QUIZ = "06_quiz"
    TEACH_BACK = "07_teach_back"
    REVISION = "08_revision"
    EXAM_SIM = "09_exam_simulation"
    CHALLENGE = "10_challenge_transfer"


@dataclass
class Draft:
    text: str
    steps: list[str] = field(default_factory=list)
    payload: dict[str, Any] = field(default_factory=dict)
    allow_llm_polish: bool = False


def recommend_mode(tier: int, last_token: Optional[str]) -> Mode:
    if last_token == "E02" or tier <= 1:
        return Mode.STEP_BY_STEP
    if last_token:
        return Mode.MISTAKE_REPAIR
    if tier >= 3:
        return Mode.CHALLENGE
    return Mode.QUIZ


def explain(concept: Concept) -> Draft:
    card = concept.card()
    return Draft(
        f"{card['definition']} {card['key_idea']} Formula: {card['formula']}. "
        f"Watch out: {card['common_mistake']}",
        payload={"card": card}, allow_llm_polish=True,
    )


def step_by_step(concept: Concept, stage: int) -> Draft:
    example = faded_example(concept, stage)
    lines = [f"{s['equation']}  ({s['note']})" for s in example["shown_steps"]]
    prompt = f"{example['problem']} " + " ".join(lines)
    if example["blank_steps"]:
        prompt += f" Now you complete the remaining {example['blank_steps']} step(s)."
    shown = [s["equation"] for s in example["shown_steps"]] if concept.subject == "Mathematics" else []
    return Draft(prompt.strip(), steps=shown if len(shown) >= 2 else [],
                 payload={"example": example, "next_stage": min(stage + 1, len(FADE_STAGES) - 1)})


def hint(concept: Concept, item: Item, level: int) -> Draft:
    """Three stages: name the idea, name the next move, set up the start. Never the answer."""
    level = max(1, min(level, 3))
    ladder = [
        f"Think about this idea: {concept.key_idea}",
        f"Useful relation: {concept.formula}. Which quantities in the question fit it?",
        (f"Start from {item.start_equation} and do one operation to both sides."
         if item.start_equation else
         f"Write down the known values from the question, then apply: {concept.formula}."),
    ]
    text = ladder[level - 1]
    # Fall back through safer rungs if a template's wording would reveal the value.
    while leaks_answer(text, item.answer) and level > 1:
        level -= 1
        text = ladder[level - 1]
    if leaks_answer(text, item.answer):
        text = "Re-read the question and list what you know and what you must find."
    return Draft(text, payload={"hint_level": level, "max_level": 3, "item_id": item.item_id})


def socratic(concept: Concept, turn: int) -> Draft:
    question = concept.socratic[turn % len(concept.socratic)]
    return Draft(question, payload={"turn": turn + 1, "asks_student": True}, allow_llm_polish=False)


def mistake_repair(concept: Concept, token: Optional[str], attribution: Optional[dict]) -> Draft:
    opener = (attribution or {}).get("succeeded", "You have already done useful work on this.")
    fix = (attribution or {}).get("fix", concept.common_mistake)
    example = faded_example(concept, 1)
    return Draft(
        f"{opener} {fix} A common trap here: {concept.common_mistake}",
        payload={"error_token": token, "attribution": attribution, "repair_example": example},
    )


def _choose_item(concept: Concept, seen: set[str], hardest: bool = False) -> Item:
    pool = [i for i in items_for(concept.concept_id) if i.item_id not in seen] or items_for(concept.concept_id)
    pool.sort(key=lambda i: (i.b, i.item_id))
    return pool[-1] if hardest else pool[len(pool) // 2]


def quiz(concept: Concept, seen: set[str]) -> tuple[Draft, Item]:
    item = _choose_item(concept, seen)
    return Draft(item.prompt, payload={"item": item.public_view(),
                                       "confidence_options": ["Sure", "Unsure", "Guess"]}), item


def grade_answer(item: Item, response: str, confidence: Optional[str]) -> dict[str, Any]:
    correct = grade(item, response)
    return {
        "correct": correct,
        "confidence": confidence,
        "entrenched_misconception": not correct and confidence == "Sure",
        "lucky_guess": correct and confidence == "Guess",
    }


def teach_back_rubric(concept: Concept, explanation: str) -> dict[str, Any]:
    """0-3: accurate key terms, causal reasoning, a concrete example or relation.

    Text copied from the concept card, or under 12 words, scores 0.
    """
    words = re.findall(r"\w+", explanation.lower())
    normalized = " ".join(words)
    card_text = " ".join(re.findall(r"\w+", " ".join(concept.card().values()).lower()))
    copied = len(words) >= 12 and any(
        " ".join(words[i:i + 12]) in card_text for i in range(0, len(words) - 11)
    )
    if len(words) < 12 or copied:
        criteria = {"key_terms": False, "reasoning": False, "example": False}
    else:
        hits = sum(1 for term in concept.keywords if term in normalized)
        criteria = {
            "key_terms": hits >= 2,
            "reasoning": bool(re.search(
                r"\b(because|since|therefore|so that|that is why|this means|kyunki|isliye|iska matlab)\b"
                r"|क्योंकि|इसलिए", explanation, re.IGNORECASE)),
            "example": bool(re.search(r"\d|\bfor example\b|\bjaise\b|\bexample\b|जैसे", explanation, re.IGNORECASE)),
        }
    score = sum(criteria.values())
    return {"score": score, "criteria": criteria, "passed": score >= TEACH_BACK_PASS}


def revision(concept: Concept) -> Draft:
    return Draft(
        f"{concept.title}. Remember: {concept.key_idea} Formula: {concept.formula}. "
        f"Avoid: {concept.common_mistake}",
        payload={"flashcards": [
            {"front": f"Formula for {concept.title}?", "back": concept.formula},
            {"front": "Common mistake?", "back": concept.common_mistake},
            {"front": "Key idea?", "back": concept.key_idea},
        ]},
    )


def exam_paper(concepts: list[Concept], seed: str, count: int = 10) -> list[Item]:
    """A fixed mixed paper for a session, with no hints available."""
    rng = random.Random(seed)
    paper: list[Item] = []
    for index in range(count):
        pool = items_for(concepts[index % len(concepts)].concept_id)
        paper.append(rng.choice(pool))
    return paper


def grade_paper(paper_ids: list[str], answers: dict[str, str]) -> dict[str, Any]:
    results = []
    for item_id in paper_ids:
        item = get_item(item_id)
        response = answers.get(item_id, "")
        results.append({"item_id": item_id, "concept_id": item.concept_id, "attempted": bool(response.strip()),
                        "correct": bool(response.strip()) and grade(item, response),
                        "answer": f"{item.answer} {item.unit}".strip()})
    return {"score": sum(r["correct"] for r in results), "total": len(results), "results": results}


def challenge(concept: Concept, seen: set[str]) -> tuple[Draft, Item]:
    item = _choose_item(concept, seen, hardest=True)
    return Draft(f"Challenge, with no hints: {item.prompt}",
                 payload={"item": item.public_view(), "unhinted": True,
                          "confidence_options": ["Sure", "Unsure", "Guess"]}), item


def concept_or_none(concept_id: Optional[str]) -> Optional[Concept]:
    return CONCEPTS_BY_ID.get(concept_id) if concept_id else None

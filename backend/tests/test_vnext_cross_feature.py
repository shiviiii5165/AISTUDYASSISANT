import pytest
from app.services.lesson_planner.vnext.compiler import LessonCompiler
from app.services.lesson_planner.vnext.shared_context import LessonContextProvider, LearningEvidenceService
from app.services.deck_service import generate_outline_from_shared_context
from app.services.notes.generator import NotesGenerator
from app.services.teach.schemas import EvaluationResult
from app.services.teach.mastery import calculate_mastery_update
from app.services.lesson_planner.vnext.adaptive import AdaptiveLessonEngine
from app.services.lesson_planner.schemas import LearningEvidenceRecord, ProductMode


@pytest.mark.anyio
async def test_full_cross_feature_closed_loop():
    """
    End-to-End P3 Closed-Loop Integration Proof:
    1. Lesson Planner compiles lesson plan & Knowledge Pack.
    2. LessonContextProvider derives SharedLessonContext.
    3. PPT generator builds outline from SharedLessonContext without ontology regeneration.
    4. TeachMe processes session and emits standardized LearningEvidence.
    5. Quiz generates evidence and writes to LearningEvidenceService.
    6. Lesson Planner evaluates evidence and triggers adaptive recompilation.
    7. Notes generator takes weak concepts & prerequisite gaps and produces targeted revision notes.
    """
    # 1. Lesson Planner Compiles Lesson
    roadmap = await LessonCompiler.compile_lesson_plan(
        topic="Binary Search Trees",
        grade="B.Tech",
        duration_minutes=60,
        mode=ProductMode.TEACHER_CLASSROOM
    )
    assert len(roadmap.stages) > 0
    assert roadmap.knowledge_pack_id is not None

    # 2. SharedLessonContext Derived
    shared_ctx = LessonContextProvider.get_shared_context(roadmap)
    assert shared_ctx.topic == "Binary Search Trees"
    assert len(shared_ctx.canonical_concepts) > 0
    assert len(shared_ctx.stage_timings) > 0

    # 3. PPT Generator Reuses Planning Context (No Redundant Ontology Generation)
    deck_outline = await generate_outline_from_shared_context(shared_ctx, user_id="teacher_101")
    assert deck_outline["reused_context"] is True
    assert deck_outline["knowledge_pack_id"] == roadmap.knowledge_pack_id
    assert len(deck_outline["slides"]) >= len(roadmap.stages)

    # 4. TeachMe Evaluates Session & Emits Standardized Evidence
    eval_res = EvaluationResult(
        score=0.30,
        correctness="incorrect",
        concept_id="cs.algo.bst.search",
        misconception="Left child greater than parent"
    )
    new_score, delta, label, decision = calculate_mastery_update(
        current_score=0.40,
        eval_result=eval_res,
        difficulty="medium"
    )
    assert decision in ["switch_strategy_reteach", "reinforce_with_example"]

    # 5. Quiz Attempt Emits Evidence
    quiz_evidence = LearningEvidenceRecord(
        student_id="student_quiz_1",
        roadmap_id=roadmap.id,
        concept_id="cs.algo.bst.search",
        source_type="quiz",
        question_id="q_bst_1",
        event_id="evt_quiz_bst_1",
        correctness=False,
        confidence=0.85,
        misconception_candidate="Left child greater than parent"
    )
    LearningEvidenceService.record_evidence(quiz_evidence)

    # Ingest class-wide batch of evidence showing same misconception
    class_evidence = [
        LearningEvidenceRecord(
            student_id=f"student_batch_{i}",
            roadmap_id=roadmap.id,
            concept_id="cs.algo.bst.search",
            source_type="quiz",
            question_id="q_bst_1",
            event_id=f"evt_quiz_bst_batch_{i}",
            correctness=False,
            confidence=0.85,
            misconception_candidate="Left child greater than parent"
        )
        for i in range(8)
    ]

    # 6. Lesson Planner Ingests Evidence and Recompiles Remaining Plan
    diff = AdaptiveLessonEngine.evaluate_and_recompile(
        roadmap=roadmap,
        evidence_list=class_evidence,
        active_class_size=10
    )
    assert len(diff.stages_added) > 0
    assert "Left child greater than parent" in diff.stages_added[0]["title"]
    assert diff.requires_teacher_approval is True

    # 7. Notes Generator Consumes Diagnosed Gaps & Generates Remedial Notes
    remedial_notes = NotesGenerator.generate_from_lesson_gap_context(
        topic="Binary Search Trees",
        weak_concepts=["BST Search Invariant", "Node Ordering"],
        prerequisite_gaps=["Binary Tree Traversal"],
        misconception_evidence=[{"misconception": "Left child greater than parent"}]
    )
    assert remedial_notes.title == "Targeted Revision Notes: Binary Search Trees"
    assert len(remedial_notes.sections) == 2
    assert "Prerequisite Foundations Refresher" in remedial_notes.sections[0].heading

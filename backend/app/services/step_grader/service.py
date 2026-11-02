"""
LearnByGenie — Feature 8: Step-Grader & Reasoning Diagnostics Engine Service
=============================================================================
Canonical subject-agnostic coordinator (§2, §39):
- Validates multi-step solutions step-by-step
- Pinpoints first wrong step (ROOT_ERROR)
- Disentangles downstream arithmetic consequences (DOWNSTREAM_ERROR) from root errors
- Ingests exactly ONE canonical root mistake into Mistake DNA (zero double counting)
- Submits assistance-aware evidence to Mastery Graph (learner_skill_evidence)
- Preserves explicit uncertainty without fake percentages
- Supports solution versioning (resubmissions) and bounded Socratic Tutor handoffs
"""
import re
import uuid
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone

from app.core.logging import logger
from app.services.step_grader.schemas import (
    StepGraderSession, StepGraderAttempt, GradedStep, StepGraderResult,
    TutorHandoffContext, CapabilityMatrixItem, StructuredRubric,
    StepType, StepValidationStatus, ValidatorType, ConfidenceClass,
    OverallOutcome, SessionStatus, ErrorType
)
from app.services.step_grader.adapters import (
    StepGraderAdapter, get_default_adapters, MathStepAdapter,
    PhysicsStepAdapter, ChemistryStepAdapter, CSReasoningAdapter,
    GenericSequenceAdapter
)
from app.services.step_grader.policy import get_step_grader_policy, StepGraderPolicy
from app.services.step_grader.repository import StepGraderRepository

# Feature 3 & Feature 5 integrations (§20, §21, §23)
from app.services.mastery.service import MasteryGraphService
from app.services.mastery.schemas import EvidenceSource, AssistanceLevel
from app.services.mistake_dna.service import MistakeDNAService
from app.services.mistake_dna.schemas import (
    MistakeCandidate, MistakeSourceType, AssistanceLevel as MistakeAssistanceLevel
)
from app.services.diagnostic.curriculum_blueprint import get_skill


class StepGraderService:
    """
    Subject-agnostic reasoning diagnostics and step-grading engine.
    Orchestration remains completely domain-independent; validation delegates to adapters.
    """

    _adapters: List[StepGraderAdapter] = get_default_adapters()

    @classmethod
    def register_adapter(cls, adapter: StepGraderAdapter, insert_at_front: bool = True) -> None:
        """Allows registering custom or synthetic domain adapters (§40, §41)."""
        if insert_at_front:
            cls._adapters.insert(0, adapter)
        else:
            cls._adapters.append(adapter)

    @classmethod
    def get_adapter_for(cls, subject: str, skill_id: Optional[str], raw_text: str) -> StepGraderAdapter:
        """Selects the first matching domain adapter, falling back to GenericSequenceAdapter."""
        for adapter in cls._adapters:
            if adapter.can_handle(subject, skill_id, raw_text):
                return adapter
        return GenericSequenceAdapter()

    # ─── 1. STEP PARSER ────────────────────────────────────────────────────────

    @classmethod
    def parse_steps(cls, raw_input: str, adapter: Optional[StepGraderAdapter] = None) -> List[Tuple[int, str, StepType]]:
        """
        Parses raw multiline or numbered student solution into structured step tokens (§4, §6).
        Does NOT overwrite or destroy raw text.
        """
        lines = [line.strip() for line in raw_input.strip().splitlines() if line.strip()]
        parsed: List[Tuple[int, str, StepType]] = []

        step_idx = 1
        for line in lines:
            # Check if line has numbering like "1. ", "Step 1: ", etc.
            step_type = adapter.infer_step_type(line, step_idx) if adapter else StepType.TRANSFORMATION
            parsed.append((step_idx, line, step_type))
            step_idx += 1

        return parsed

    # ─── 2. GRADE SOLUTION ────────────────────────────────────────────────────

    @classmethod
    def grade_solution(
        cls,
        user_id: str,
        subject: str,
        question_text: str,
        raw_input: str,
        skill_id: Optional[str] = None,
        assistance_level: AssistanceLevel = AssistanceLevel.INDEPENDENT,
        session_id: Optional[str] = None,
        parent_attempt_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        rubric: Optional[Dict[str, Any]] = None,
        audience_level: str = "standard"  # "young" (Class 3-5), "standard" (Class 8-10), "advanced" (JEE/UG)
    ) -> StepGraderResult:
        """
        Authoritative solution grading workflow (§17, §38):
        1. Checks database idempotency
        2. Normalizes & parses steps
        3. Identifies first wrong step
        4. Classifies downstream vs root error
        5. Closes loop with Mistake DNA & Mastery Graph
        """
        policy: StepGraderPolicy = get_step_grader_policy("1.0.0")

        # ─── A. IDEMPOTENCY CHECK (§34) ───────────────────────────────────────
        if idempotency_key:
            existing_attempt = StepGraderRepository.find_attempt_by_idempotency_key(user_id, idempotency_key)
            if existing_attempt:
                existing_steps = StepGraderRepository.get_steps_for_attempt(existing_attempt.id, user_id)
                return cls._build_result_from_attempt(existing_attempt, existing_steps, skill_id)

        return cls._execute_grade_solution(
            user_id=user_id,
            subject=subject,
            question_text=question_text,
            raw_input=raw_input,
            skill_id=skill_id,
            assistance_level=assistance_level,
            session_id=session_id,
            parent_attempt_id=parent_attempt_id,
            idempotency_key=idempotency_key,
            rubric=rubric,
            audience_level=audience_level,
        )

    @classmethod
    def _execute_grade_solution(
        cls,
        user_id: str,
        subject: str,
        question_text: str,
        raw_input: str,
        skill_id: Optional[str] = None,
        assistance_level: AssistanceLevel = AssistanceLevel.INDEPENDENT,
        session_id: Optional[str] = None,
        parent_attempt_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        rubric: Optional[Dict[str, Any]] = None,
        audience_level: str = "standard"
    ) -> StepGraderResult:
        policy: StepGraderPolicy = get_step_grader_policy("1.0.0")

        # Resolve canonical skill ID for database foreign keys
        db_skill_id = skill_id if (skill_id and get_skill(skill_id) is not None) else None

        # ─── B. SESSION MANAGEMENT & ATOMIC SEQUENCE ALLOCATION (§31, §35) ────
        session: Optional[StepGraderSession] = None
        if session_id:
            session = StepGraderRepository.get_session(session_id, user_id)
            if not session:
                raise PermissionError(f"Unauthorized or non-existent session {session_id}")
            attempt_seq = StepGraderRepository.allocate_next_sequence(session.id, user_id)
            session.total_attempts = max(session.total_attempts, attempt_seq)
        else:
            # Deterministic session ID for idempotent initial submission
            # Guarantees concurrent workers for the same initial request target the identical session (§34)
            sess_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{user_id}:{idempotency_key}")) if idempotency_key else str(uuid.uuid4())
            existing_sess = StepGraderRepository.get_session(sess_id, user_id)
            if existing_sess:
                session = existing_sess
                attempt_seq = StepGraderRepository.allocate_next_sequence(session.id, user_id)
            else:
                session = StepGraderSession(
                    id=sess_id,
                    user_id=user_id,
                    subject=subject,
                    skill_id=db_skill_id,
                    source_type="STUDENT_DIRECT",
                    total_attempts=1,
                    status=SessionStatus.ACTIVE
                )
                attempt_seq = 1

        # ─── C. ADAPTER RESOLUTION & PARSING (§40) ────────────────────────────
        adapter = cls.get_adapter_for(subject, skill_id, raw_input)
        parsed_steps = cls.parse_steps(raw_input, adapter)

        if not parsed_steps:
            # Empty input edge case
            attempt = StepGraderAttempt(
                session_id=session.id,
                user_id=user_id,
                attempt_sequence=attempt_seq,
                parent_attempt_id=parent_attempt_id,
                question_text=question_text,
                raw_input=raw_input,
                overall_outcome=OverallOutcome.UNRESOLVED,
                confidence_class=ConfidenceClass.LOW,
                repair_recommendation="Please enter at least one step of your solution to check."
            )
            StepGraderRepository.save_session(session)
            StepGraderRepository.save_attempt(attempt)
            return cls._build_result_from_attempt(attempt, [], skill_id)

        # ─── D. STEP VALIDATION & ERROR CASCADE (§8, §9) ──────────────────────
        graded_steps: List[GradedStep] = []
        downstream_indices: List[int] = []
        root_error_step: Optional[GradedStep] = None
        first_wrong_step_idx: Optional[int] = None
        overall_confidence: ConfidenceClass = ConfidenceClass.HIGH

        context: Dict[str, Any] = {"rubric": rubric, "audience_level": audience_level}

        for step_idx, raw_text, step_type in parsed_steps:
            norm_expr = re.sub(r'^(?:step\s*)?\d+[\.:\)]\s*', '', raw_text.strip(), flags=re.IGNORECASE)

            # Validate current step
            val_res = adapter.validate_step(
                step_index=step_idx,
                raw_text=raw_text,
                prev_steps=graded_steps,
                question_text=question_text,
                context=context
            )

            # Confidence degradation
            if val_res.confidence == ConfidenceClass.LOW:
                overall_confidence = ConfidenceClass.LOW
            elif val_res.confidence == ConfidenceClass.MODERATE and overall_confidence != ConfidenceClass.LOW:
                overall_confidence = ConfidenceClass.MODERATE

            step_status = val_res.validation_status
            is_root = False
            feedback = val_res.feedback
            err_type = val_res.error_type
            err_subtype = val_res.error_subtype

            # Error Cascade Decision Tree (§8, §9)
            if step_status == StepValidationStatus.ROOT_ERROR:
                if root_error_step is None:
                    # EARLIEST INVALID STEP -> ROOT ERROR
                    is_root = True
                    first_wrong_step_idx = step_idx
                    root_error_step = GradedStep(
                        step_index=step_idx,
                        raw_text=raw_text,
                        normalized_expression=norm_expr,
                        step_type=step_type,
                        validation_status=StepValidationStatus.ROOT_ERROR,
                        validator_type=val_res.validator_type,
                        confidence=val_res.confidence,
                        is_root_error=True,
                        error_type=err_type,
                        error_subtype=err_subtype,
                        feedback=feedback
                    )
                else:
                    # Subsequent issue: test if it's a downstream consequence
                    is_downstream = adapter.check_downstream_derivation(
                        corrupted_step=root_error_step,
                        current_raw_text=raw_text,
                        prev_steps=graded_steps
                    )
                    if is_downstream:
                        step_status = StepValidationStatus.DOWNSTREAM_ERROR
                        downstream_indices.append(step_idx)
                        feedback = f"Step {step_idx} follows logically from the earlier equation, but depends on the issue in Step {first_wrong_step_idx}."
                        err_type = None
                        err_subtype = None
                    else:
                        step_status = StepValidationStatus.INDEPENDENT_ERROR
            elif step_status == StepValidationStatus.VALID_STEP and root_error_step is not None:
                # If a valid mathematical operation was performed on an already corrupted state:
                # It is a DOWNSTREAM consequence (§9)
                is_downstream = adapter.check_downstream_derivation(
                    corrupted_step=root_error_step,
                    current_raw_text=raw_text,
                    prev_steps=graded_steps
                )
                if is_downstream:
                    step_status = StepValidationStatus.DOWNSTREAM_ERROR
                    downstream_indices.append(step_idx)
                    feedback = f"Step {step_idx} calculates correctly from Step {first_wrong_step_idx}, but inherits its value."

            st = GradedStep(
                step_index=step_idx,
                raw_text=raw_text,
                normalized_expression=norm_expr,
                step_type=step_type,
                validation_status=step_status,
                validator_type=val_res.validator_type,
                confidence=val_res.confidence,
                is_root_error=is_root,
                error_type=err_type,
                error_subtype=err_subtype,
                feedback=feedback
            )
            graded_steps.append(st)

        # ─── E. OVERALL OUTCOME & FEEDBACK SYNTHESIS ───────────────────────────
        if any(s.validation_status == StepValidationStatus.UNCERTAIN for s in graded_steps):
            overall_outcome = OverallOutcome.AMBIGUOUS_REASONING
            repair_recommendation = "Some steps could not be verified with complete certainty. Review the highlighted steps."
        elif root_error_step is not None:
            overall_outcome = OverallOutcome.ROOT_ERROR_DETECTED
            repair_recommendation = cls._format_supportive_recommendation(
                root_error_step, audience_level
            )
        else:
            overall_outcome = OverallOutcome.ALL_STEPS_VALID
            repair_recommendation = "All steps are logically and mathematically sound! Great work."

        # ─── F. PERSIST ATTEMPT & STEPS ───────────────────────────────────────
        attempt = StepGraderAttempt(
            session_id=session.id,
            user_id=user_id,
            attempt_sequence=attempt_seq,
            parent_attempt_id=parent_attempt_id,
            question_text=question_text,
            raw_input=raw_input,
            assistance_level=assistance_level,
            overall_outcome=overall_outcome,
            first_wrong_step_index=first_wrong_step_idx,
            validated_step_count=len(graded_steps),
            root_error_type=root_error_step.error_type if root_error_step else None,
            root_error_subtype=root_error_step.error_subtype if root_error_step else None,
            confidence_class=overall_confidence,
            repair_recommendation=repair_recommendation,
            idempotency_key=idempotency_key or ""
        )

        session.current_attempt_id = attempt.id
        StepGraderRepository.save_session(session)
        saved_attempt = StepGraderRepository.save_attempt(attempt)
        if saved_attempt.id != attempt.id:
            existing_steps = StepGraderRepository.get_steps_for_attempt(saved_attempt.id, user_id)
            return cls._build_result_from_attempt(saved_attempt, existing_steps, skill_id)
        StepGraderRepository.save_steps(attempt.id, graded_steps, user_id, session.id)

        # ─── G. CLOSED LOOP: MISTAKE DNA INTEGRATION (§21, §22) ────────────────
        if root_error_step and root_error_step.error_type:
            try:
                # Provide canonical feedback signal so MistakeClassifier retains the root error type (§21)
                fb_sig = root_error_step.feedback
                if root_error_step.error_type == ErrorType.SIGN_OR_NOTATION:
                    fb_sig = f"sign change error. {root_error_step.feedback}"
                elif root_error_step.error_type == ErrorType.CALCULATION:
                    fb_sig = f"arithmetic calculation slip. {root_error_step.feedback}"
                elif root_error_step.error_type == ErrorType.PROCEDURAL:
                    fb_sig = f"procedural transposition error. {root_error_step.feedback}"
                elif root_error_step.error_type == ErrorType.UNIT_OR_DIMENSION:
                    fb_sig = f"unit mismatch error. {root_error_step.feedback}"

                candidate = MistakeCandidate(
                    user_id=user_id,
                    skill_id=db_skill_id or "GENERAL_REASONING",
                    subject=subject,
                    source_type=MistakeSourceType.STEP_GRADER,
                    source_record_id=f"step_attempt_{attempt.id}",
                    question_reference=question_text[:120] if question_text else "Step-by-step reasoning",
                    student_response=root_error_step.raw_text,
                    correct_answer="",
                    prompt_text=question_text,
                    feedback_reason=fb_sig,
                    primary_error_type=root_error_step.error_type,
                    error_subtype=root_error_step.error_subtype or "",
                    error_summary=root_error_step.feedback,
                    confidence_class=overall_confidence,
                    assistance_level=MistakeAssistanceLevel.INDEPENDENT,
                    metadata={
                        "step_index": root_error_step.step_index,
                        "session_id": session.id,
                        "attempt_id": attempt.id,
                        "raw_skill_id": skill_id
                    }
                )
                MistakeDNAService.ingest_error_candidate(candidate)
            except Exception as e:
                logger.warning(f"[StepGraderService] Mistake DNA ingestion note: {e}")

        # ─── H. CLOSED LOOP: MASTERY GRAPH EVIDENCE (§23, §24) ────────────────
        if db_skill_id and policy.should_emit_mastery_evidence(overall_outcome, overall_confidence, assistance_level):
            try:
                is_correct = (overall_outcome == OverallOutcome.ALL_STEPS_VALID)
                MasteryGraphService.ingest_evidence(
                    user_id=user_id,
                    skill_id=db_skill_id,
                    source_type=EvidenceSource.STEP_GRADER,
                    source_record_id=f"step_attempt_{attempt.id}",
                    correctness=is_correct,
                    independence_level=assistance_level,
                    metadata={
                        "session_id": session.id,
                        "attempt_id": attempt.id,
                        "first_wrong_step": first_wrong_step_idx
                    }
                )
            except Exception as e:
                logger.warning(f"[StepGraderService] Mastery Graph evidence ingestion note: {e}")

        return cls._build_result_from_attempt(attempt, graded_steps, skill_id)

    # ─── 3. RESUBMISSION / SOLUTION VERSIONING (§35) ──────────────────────────

    @classmethod
    def resubmit_solution(
        cls,
        session_id: str,
        user_id: str,
        updated_raw_input: str,
        assistance_level: AssistanceLevel = AssistanceLevel.INDEPENDENT,
        rubric: Optional[Dict[str, Any]] = None,
        audience_level: str = "standard"
    ) -> StepGraderResult:
        """
        Resubmits an edited solution under an existing session.
        Preserves complete attempt lineage and incremented attempt sequence (§35).
        """
        session = StepGraderRepository.get_session(session_id, user_id)
        if not session:
            raise ValueError(f"Session {session_id} not found or unauthorized for user {user_id}")

        prev_attempts = StepGraderRepository.get_attempts_for_session(session_id, user_id)
        parent_attempt_id = prev_attempts[-1].id if prev_attempts else None
        question_text = prev_attempts[-1].question_text if prev_attempts else ""

        return cls.grade_solution(
            user_id=user_id,
            subject=session.subject,
            question_text=question_text,
            raw_input=updated_raw_input,
            skill_id=session.skill_id,
            assistance_level=assistance_level,
            session_id=session_id,
            parent_attempt_id=parent_attempt_id,
            rubric=rubric,
            audience_level=audience_level
        )

    # ─── 4. BOUNDED TUTOR HANDOFF CONTEXT (§20) ───────────────────────────────

    @classmethod
    def get_tutor_context(cls, attempt_id: str, user_id: str) -> TutorHandoffContext:
        """
        Extracts bounded context for Socratic Tutor review.
        Only transmits the specific root error and relevant skill/prerequisite (§20).
        """
        attempt = StepGraderRepository.get_attempt(attempt_id, user_id)
        if not attempt:
            raise ValueError(f"Attempt {attempt_id} not found or unauthorized for user {user_id}")

        steps = StepGraderRepository.get_steps_for_attempt(attempt_id, user_id)
        root_step = next((s for s in steps if s.is_root_error), None)

        skill_obj = get_skill(attempt.metadata.get("skill_id", "")) if attempt.metadata else None
        skill_name = skill_obj.skill_name if skill_obj else attempt.metadata.get("skill_id", "General Reasoning")

        if not root_step:
            # Fallback if all steps were valid or ambiguous
            return TutorHandoffContext(
                session_id=attempt.session_id,
                attempt_id=attempt.id,
                skill_id=skill_obj.id if skill_obj else None,
                skill_name=skill_name,
                first_wrong_step_index=0,
                step_raw_text="",
                error_type="NONE",
                feedback="All steps appear valid.",
                question_text=attempt.question_text
            )

        return TutorHandoffContext(
            session_id=attempt.session_id,
            attempt_id=attempt.id,
            skill_id=skill_obj.id if skill_obj else None,
            skill_name=skill_name,
            first_wrong_step_index=root_step.step_index,
            step_raw_text=root_step.raw_text,
            error_type=root_step.error_type.value if root_step.error_type else "REASONING",
            error_subtype=root_step.error_subtype,
            feedback=root_step.feedback,
            related_prerequisite=skill_obj.prerequisites[0] if (skill_obj and skill_obj.prerequisites) else None,
            question_text=attempt.question_text
        )

    # ─── 5. GRADING CAPABILITY MATRIX (§43) ───────────────────────────────────

    @classmethod
    def get_capability_matrix(cls) -> List[CapabilityMatrixItem]:
        """Produces honest capability matrix separating engine support from coverage (§42, §43)."""
        return [
            CapabilityMatrixItem(
                subject="Mathematics",
                skill_name="Linear Equations & Transformations",
                step_types_supported=["SETUP", "TRANSFORMATION", "CALCULATION", "CONCLUSION"],
                validator_type=ValidatorType.DETERMINISTIC,
                deterministic_support=True,
                rubric_support=True,
                confidence_capability="HIGH",
                notes="Deterministic AST equivalence and algebraic sign transposition detection."
            ),
            CapabilityMatrixItem(
                subject="Physics",
                skill_name="Formula Substitution & Unit Consistency",
                step_types_supported=["SETUP", "SUBSTITUTION", "CALCULATION", "CONCLUSION"],
                validator_type=ValidatorType.DOMAIN_RULE,
                deterministic_support=True,
                rubric_support=True,
                confidence_capability="HIGH",
                notes="Verifies SI unit consistency and numeric progression."
            ),
            CapabilityMatrixItem(
                subject="Chemistry",
                skill_name="Stoichiometry & Mole Relationships",
                step_types_supported=["SETUP", "RULE_APPLICATION", "SUBSTITUTION", "CALCULATION"],
                validator_type=ValidatorType.DOMAIN_RULE,
                deterministic_support=True,
                rubric_support=True,
                confidence_capability="HIGH",
                notes="Verifies molar ratios and quantitative transformations."
            ),
            CapabilityMatrixItem(
                subject="Computer Science",
                skill_name="Algorithm Dry Runs & Condition Bounds",
                step_types_supported=["SETUP", "TRANSFORMATION", "INFERENCE", "CONCLUSION"],
                validator_type=ValidatorType.DOMAIN_RULE,
                deterministic_support=True,
                rubric_support=True,
                confidence_capability="HIGH",
                notes="Checks state transitions and loop bounds without arbitrary code execution."
            ),
            CapabilityMatrixItem(
                subject="Biology",
                skill_name="Ordered Biological Processes",
                step_types_supported=["SETUP", "EXPLANATION", "INFERENCE", "CONCLUSION"],
                validator_type=ValidatorType.RUBRIC,
                deterministic_support=False,
                rubric_support=True,
                confidence_capability="MODERATE",
                notes="Structured rubric matching with explicit uncertainty for ambiguous text."
            ),
            CapabilityMatrixItem(
                subject="Dynamic Domain",
                skill_name="Synthetic Subject Extension",
                step_types_supported=["SETUP", "RULE_APPLICATION", "TRANSFORMATION"],
                validator_type=ValidatorType.RUBRIC,
                deterministic_support=False,
                rubric_support=True,
                confidence_capability="MODERATE",
                notes="Dynamic domain adaptation without core orchestrator modification."
            )
        ]

    # ─── INTERNAL HELPERS ─────────────────────────────────────────────────────

    @classmethod
    def _format_supportive_recommendation(cls, root_step: GradedStep, audience_level: str) -> str:
        """Generates age-adapted, supportive, no-shame feedback (§18, §47, §48)."""
        idx = root_step.step_index
        fb = root_step.feedback

        if audience_level == "young":
            return f"Let's check Step {idx} together. {fb} Try fixing this step first!"
        elif audience_level == "advanced":
            return f"First issue detected at Step {idx}: {fb} Correcting this transformation will resolve subsequent downstream derivations."
        else:
            return f"Step {idx} needs another look: {fb} Try adjusting Step {idx} and re-checking."

    @classmethod
    def _build_result_from_attempt(
        cls,
        attempt: StepGraderAttempt,
        steps: List[GradedStep],
        skill_id: Optional[str]
    ) -> StepGraderResult:
        downstream_indices = [
            s.step_index for s in steps if s.validation_status == StepValidationStatus.DOWNSTREAM_ERROR
        ]
        return StepGraderResult(
            session_id=attempt.session_id,
            attempt_id=attempt.id,
            attempt_sequence=attempt.attempt_sequence,
            overall_outcome=attempt.overall_outcome,
            first_wrong_step=attempt.first_wrong_step_index,
            validated_steps=steps,
            downstream_steps=downstream_indices,
            error_type=attempt.root_error_type,
            error_subtype=attempt.root_error_subtype,
            confidence=attempt.confidence_class,
            skill_id=skill_id,
            feedback_summary=attempt.repair_recommendation,
            recommended_next_action="Try fixing Step " + str(attempt.first_wrong_step_index) if attempt.first_wrong_step_index else "Continue learning",
            can_review_with_tutor=True
        )

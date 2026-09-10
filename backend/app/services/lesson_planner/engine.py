from typing import List, Dict, Any, Tuple, Optional, Set
from datetime import datetime, timezone
from .schemas import (
    LearningRoadmap, RoadmapStage, StageStatus, StageReadiness, 
    NextBestAction, ResourceType, ResourceStatus, ResourceRecommendation,
    BloomLevel, StageActivity, StageDifferentiation, RoadmapEvent, ClassType,
    StageAction
)


class TimeBudgetEngine:
    """
    Pure Python deterministic engine for time budgeting.
    Zero LLM arithmetic.
    """

    @staticmethod
    def validate_and_adjust_timing(
        roadmap: LearningRoadmap,
        exact_mode: bool = False
    ) -> Tuple[bool, List[str]]:
        warnings: List[str] = []
        total_time = sum(stage.duration_minutes for stage in roadmap.stages)
        target = roadmap.target_duration_minutes

        if total_time > target:
            warnings.append(f"Total stage duration ({total_time}m) exceeds lesson target ({target}m) by {total_time - target}m.")
            return False, warnings

        if exact_mode and total_time < target:
            warnings.append(f"Total stage duration ({total_time}m) is under target ({target}m) by {target - total_time}m.")
            return False, warnings

        if total_time < int(target * 0.7):
            warnings.append(f"Total time ({total_time}m) is significantly under-allocated (target is {target}m).")

        # Validate sub-activities within each stage
        for stage in roadmap.stages:
            if stage.activities:
                stage_act_sum = sum(act.duration_minutes for act in stage.activities)
                if stage_act_sum > stage.duration_minutes:
                    warnings.append(
                        f"Stage '{stage.title}' activities total {stage_act_sum}m, exceeding stage budget of {stage.duration_minutes}m."
                    )
                    return False, warnings
                elif stage_act_sum < stage.duration_minutes:
                    # Auto-fill padding or minor warning
                    pass

        return True, warnings

    @staticmethod
    def auto_balance_durations(roadmap: LearningRoadmap) -> None:
        """
        Proportionally balances stage durations to match target duration.
        """
        if not roadmap.stages:
            return
        target = roadmap.target_duration_minutes
        current_sum = sum(s.duration_minutes for s in roadmap.stages) or 1
        
        allocated = 0
        for i, stage in enumerate(roadmap.stages):
            if i == len(roadmap.stages) - 1:
                stage.duration_minutes = max(5, target - allocated)
            else:
                portion = int(round((stage.duration_minutes / current_sum) * target))
                portion = max(5, portion)
                stage.duration_minutes = portion
                allocated += portion


class PrerequisiteEngine:
    """
    Evaluates concept prerequisites, readiness states, and detects prerequisite blocking.
    """

    @staticmethod
    def evaluate_readiness(
        roadmap: LearningRoadmap,
        mastery_threshold: int = 70
    ) -> None:
        """
        Deterministically evaluates stage readiness and updates stage statuses in-place.
        """
        concept_to_stage: Dict[str, RoadmapStage] = {s.concept_id: s for s in roadmap.stages}

        for i, stage in enumerate(roadmap.stages):
            # If already taught or mastered, preserve status
            if stage.status in [StageStatus.MASTERED, StageStatus.TAUGHT]:
                stage.readiness = StageReadiness.READY
                continue

            if not stage.prerequisite_ids:
                # No prerequisites needed
                stage.readiness = StageReadiness.READY
                if stage.status in [StageStatus.LOCKED, StageStatus.BLOCKED]:
                    stage.status = StageStatus.AVAILABLE
                continue

            all_prereqs_mastered = True
            any_prereq_needs_review = False
            missing_prereqs = False

            for pid in stage.prerequisite_ids:
                req_stage = concept_to_stage.get(pid)
                if not req_stage:
                    continue

                if req_stage.status == StageStatus.NEEDS_REVIEW or (req_stage.mastery > 0 and req_stage.mastery < mastery_threshold):
                    any_prereq_needs_review = True
                    all_prereqs_mastered = False
                elif req_stage.status not in [StageStatus.MASTERED, StageStatus.TAUGHT]:
                    all_prereqs_mastered = False
                    missing_prereqs = True

            if any_prereq_needs_review:
                stage.readiness = StageReadiness.REVIEW_RECOMMENDED
                stage.status = StageStatus.BLOCKED
            elif missing_prereqs:
                stage.readiness = StageReadiness.PREREQUISITE_REQUIRED
                stage.status = StageStatus.LOCKED
            else:
                stage.readiness = StageReadiness.READY
                if stage.status in [StageStatus.LOCKED, StageStatus.BLOCKED]:
                    stage.status = StageStatus.AVAILABLE


class StateMachineEngine:
    """
    Controls stage lifecycle transitions and computes the Next Best Action.
    """

    @staticmethod
    def transition_stage(
        stage: RoadmapStage,
        new_status: StageStatus
    ) -> Tuple[bool, str]:
        """
        Validates whether the requested state transition is allowed.
        """
        allowed_transitions: Dict[StageStatus, Set[StageStatus]] = {
            StageStatus.LOCKED: {StageStatus.AVAILABLE, StageStatus.BLOCKED},
            StageStatus.AVAILABLE: {StageStatus.IN_PROGRESS, StageStatus.MATERIAL_READY, StageStatus.LOCKED},
            StageStatus.MATERIAL_READY: {StageStatus.IN_PROGRESS, StageStatus.AVAILABLE},
            StageStatus.IN_PROGRESS: {StageStatus.TAUGHT, StageStatus.ASSESSMENT_PENDING, StageStatus.AVAILABLE},
            StageStatus.TAUGHT: {StageStatus.ASSESSMENT_PENDING, StageStatus.MASTERED, StageStatus.NEEDS_REVIEW},
            StageStatus.ASSESSMENT_PENDING: {StageStatus.MASTERED, StageStatus.NEEDS_REVIEW, StageStatus.TAUGHT},
            StageStatus.NEEDS_REVIEW: {StageStatus.AVAILABLE, StageStatus.IN_PROGRESS, StageStatus.TAUGHT},
            StageStatus.MASTERED: {StageStatus.TAUGHT, StageStatus.NEEDS_REVIEW},
            StageStatus.BLOCKED: {StageStatus.AVAILABLE, StageStatus.LOCKED}
        }

        valid_targets = allowed_transitions.get(stage.status, set())
        if new_status in valid_targets or new_status == stage.status:
            stage.status = new_status
            return True, "Transition successful"
        return False, f"Invalid transition from {stage.status.value} to {new_status.value}"

    @staticmethod
    def determine_next_action(roadmap: LearningRoadmap) -> NextBestAction:
        """
        Deterministically evaluates the roadmap to recommend the Next Best Action.
        """
        # 1. Any stage in needs_review?
        for stage in roadmap.stages:
            if stage.status == StageStatus.NEEDS_REVIEW:
                roadmap.next_best_action = NextBestAction.RETEACH
                return NextBestAction.RETEACH

        # 2. Any stage waiting for assessment?
        for stage in roadmap.stages:
            if stage.status == StageStatus.ASSESSMENT_PENDING:
                roadmap.next_best_action = NextBestAction.ASSESS
                return NextBestAction.ASSESS

        # 3. Any stage currently in progress?
        for stage in roadmap.stages:
            if stage.status == StageStatus.IN_PROGRESS:
                roadmap.next_best_action = NextBestAction.TEACH
                return NextBestAction.TEACH

        # 4. First available stage ready to teach
        for stage in roadmap.stages:
            if stage.status == StageStatus.AVAILABLE:
                roadmap.next_best_action = NextBestAction.TEACH
                return NextBestAction.TEACH

        # 5. Are all stages mastered/taught?
        all_done = all(s.status in [StageStatus.MASTERED, StageStatus.TAUGHT] for s in roadmap.stages)
        if all_done and roadmap.stages:
            roadmap.next_best_action = NextBestAction.ADVANCE
            return NextBestAction.ADVANCE

        roadmap.next_best_action = NextBestAction.PREREQUISITE_RECAP
        return NextBestAction.PREREQUISITE_RECAP

    @staticmethod
    def calculate_overall_progress(roadmap: LearningRoadmap) -> int:
        if not roadmap.stages:
            return 0
        total = len(roadmap.stages)
        completed = sum(1 for s in roadmap.stages if s.status in [StageStatus.MASTERED, StageStatus.TAUGHT])
        pct = int((completed / total) * 100)
        roadmap.overall_progress = pct
        return pct


class ResourceRecommenderEngine:
    """
    Computes deterministic recommendation usefulness scores and recommendation levels
    for each stage (ACTIVE: PPT, Quiz, Teach Me; FUTURE / DISABLED: YouTube Recommendations,
    Extra Learning Materials Hub). Video and Notes are removed from Lesson Planner workflow.
    """

    @staticmethod
    def evaluate_stage_resources(
        stage: RoadmapStage,
        class_type: ClassType = ClassType.INTERACTIVE_LECTURE
    ) -> List[ResourceRecommendation]:
        recommendations: List[ResourceRecommendation] = []

        title_lower = (stage.title + " " + stage.description).lower()
        has_checkpoints = bool(stage.checkpoint_questions)
        has_misconceptions = bool(stage.expected_misconceptions)
        is_lab = class_type == ClassType.LAB or "lab" in title_lower or "code" in title_lower
        is_exam_review = class_type in [ClassType.EXAM_REVIEW, ClassType.REVISION]

        # 1. PPT Deck Recommendation (ACTIVE)
        ppt_score = 0.85
        ppt_status = ResourceStatus.RECOMMENDED
        ppt_reason = "Visual structure and key diagrams enhance multi-step comprehension."
        if is_lab:
            ppt_score = 0.40
            ppt_status = ResourceStatus.OPTIONAL
            ppt_reason = "Lab session prioritizes live coding and terminal output over slides."
        elif "formula" in title_lower or "architecture" in title_lower or "diagram" in title_lower:
            ppt_score = 0.95
            ppt_status = ResourceStatus.RECOMMENDED
            ppt_reason = "Concept features architecture / structural flow ideal for presentation slides."
        
        recommendations.append(ResourceRecommendation(
            resource_type=ResourceType.PPT,
            usefulness_score=ppt_score,
            status=ppt_status,
            reason=ppt_reason
        ))

        # 2. Quiz / Assessment Recommendation (ACTIVE)
        quiz_score = 0.80 if has_checkpoints else 0.50
        quiz_status = ResourceStatus.RECOMMENDED if has_checkpoints or is_exam_review else ResourceStatus.OPTIONAL
        quiz_reason = "Formative checkpoints verify concept mastery before advancing."
        if has_misconceptions:
            quiz_score = min(1.0, quiz_score + 0.15)
            quiz_reason = "Diagnostic quiz helps identify and address anticipated student misconceptions."
        
        recommendations.append(ResourceRecommendation(
            resource_type=ResourceType.QUIZ,
            usefulness_score=quiz_score,
            status=quiz_status,
            reason=quiz_reason
        ))

        # 3. Teach Me Interactive Session (ACTIVE)
        teach_score = 0.90
        teach_status = ResourceStatus.RECOMMENDED
        teach_reason = "Socratic interactive dialogue adapts real-time to student explanations."
        if is_exam_review:
            teach_score = 0.70
            teach_status = ResourceStatus.OPTIONAL

        recommendations.append(ResourceRecommendation(
            resource_type=ResourceType.TEACH_ME,
            usefulness_score=teach_score,
            status=teach_status,
            reason=teach_reason
        ))

        # 4. YouTube Recommendations (ACTIVE)
        recommendations.append(ResourceRecommendation(
            resource_type=ResourceType.YOUTUBE_RECOMMENDATIONS,
            usefulness_score=0.90,
            status=ResourceStatus.RECOMMENDED,
            reason="Curated educational video recommendations from verified academic channels."
        ))

        # 5. Extra Learning Materials Hub (ACTIVE)
        recommendations.append(ResourceRecommendation(
            resource_type=ResourceType.EXTRA_LEARNING_MATERIALS,
            usefulness_score=0.88,
            status=ResourceStatus.RECOMMENDED,
            reason="Academic references, arXiv research papers, and official documentation."
        ))

        stage.resource_recommendations = recommendations

        # Populate formal stage action contract (All 5 active downstream actions)
        stage.actions = [
            StageAction(
                type="ppt",
                enabled=True,
                status="active",
                title="Generate PPT",
                description="Multi-slide presentation deck with diagrams and speaker notes."
            ),
            StageAction(
                type="teachme",
                enabled=True,
                status="active",
                title="TeachMe",
                description="Interactive Socratic dialogue with adaptive checkpoints."
            ),
            StageAction(
                type="quiz",
                enabled=True,
                status="active",
                title="Take Quiz",
                description="Diagnostic questions addressing key concepts and misconceptions."
            ),
            StageAction(
                type="youtube_recommendations",
                enabled=True,
                status="active",
                title="YouTube Recommendations",
                description="Curated educational videos from verified academic channels."
            ),
            StageAction(
                type="extra_learning_materials",
                enabled=True,
                status="active",
                title="Extra Learning Materials Hub",
                description="Academic references, arXiv research papers, and documentation."
            )
        ]

        return recommendations


class LessonHealthValidator:
    """
    Transparent, explainable 0-100 lesson health scoring engine.
    """

    @staticmethod
    def evaluate_health(roadmap: LearningRoadmap) -> Dict[str, Any]:
        score = 100
        reasons: List[str] = []
        warnings: List[str] = []
        actions: List[Dict[str, str]] = []

        # 1. Timing check
        is_timing_valid, timing_warnings = TimeBudgetEngine.validate_and_adjust_timing(roadmap)
        if not is_timing_valid:
            score -= 15
            warnings.extend(timing_warnings)
            actions.append({"type": "fix_timing", "label": "Rebalance Timing"})
        else:
            reasons.append("Realistic and balanced time allocation across all stages")

        # 2. Objectives and alignment check
        missing_objectives = 0
        missing_checkpoints = 0
        missing_sources = 0
        for s in roadmap.stages:
            if not s.objectives and not s.objective_ids:
                missing_objectives += 1
            if not s.checkpoint_questions:
                missing_checkpoints += 1
            if not s.source_refs:
                missing_sources += 1

        if missing_objectives > 0:
            score -= min(20, missing_objectives * 5)
            warnings.append(f"{missing_objectives} stage(s) lack explicit Bloom's learning objectives.")
            actions.append({"type": "add_objectives", "label": "Generate Objectives"})
        else:
            reasons.append("Strong objective alignment with Bloom's taxonomy")

        if missing_checkpoints > 0:
            score -= min(15, missing_checkpoints * 4)
            warnings.append(f"{missing_checkpoints} stage(s) have no formative checkpoint questions.")
            actions.append({"type": "add_checkpoints", "label": "Add Checkpoint Questions"})
        else:
            reasons.append("Comprehensive checkpoint coverage for formative assessment")

        if missing_sources == 0 and roadmap.stages:
            reasons.append("Complete source grounding across all instructional stages")

        # 3. Differentiation check
        has_diff = any(s.differentiation.core or s.differentiation.support or s.differentiation.extension for s in roadmap.stages)
        if has_diff:
            reasons.append("Multi-tier differentiation available (Core, Support, Extension)")

        score = max(10, min(100, score))
        roadmap.health_score = score

        return {
            "score": score,
            "reasons": reasons,
            "warnings": list(dict.fromkeys(warnings)),
            "recommended_fixes": actions
        }


class RemedialEngine:
    """
    Generates a targeted remedial stage when student performance on a concept is weak.
    """

    @staticmethod
    def create_remedial_stage(
        target_stage: RoadmapStage,
        weak_prereq_title: Optional[str] = None
    ) -> RoadmapStage:
        remedial_title = f"Remedial Recap: {weak_prereq_title or target_stage.title}"
        
        remedial_stage = RoadmapStage(
            id=f"remedial_{target_stage.id}_{int(datetime.now(timezone.utc).timestamp())}",
            concept_id=f"remedial_{target_stage.concept_id}",
            title=remedial_title,
            description=f"Targeted remedial review addressing core misconceptions in {target_stage.title}.",
            duration_minutes=15,
            status=StageStatus.AVAILABLE,
            readiness=StageReadiness.READY,
            is_remedial=True,
            teacher_actions=[
                f"Walk through simplified worked example for {weak_prereq_title or target_stage.title}.",
                "Highlight key distinction to clear root misconception."
            ],
            student_actions=[
                "Follow step-by-step walkthrough and answer guided micro-problem."
            ],
            evidence_of_learning=f"Student correctly solves diagnostic recap problem on {weak_prereq_title or target_stage.title}.",
            activities=[
                StageActivity(
                    type="explanation",
                    title="Misconception Breakdown",
                    description=f"Deconstruct core concept rules for {weak_prereq_title or target_stage.title}.",
                    duration_minutes=5
                ),
                StageActivity(
                    type="guided_practice",
                    title="Step-by-Step Problem Walkthrough",
                    description="Solve simplified practice case with live hints.",
                    duration_minutes=7
                ),
                StageActivity(
                    type="checkpoint",
                    title="Remedial Checkpoint",
                    description="Quick 2-question confirmation check.",
                    duration_minutes=3
                )
            ],
            checkpoint_questions=[
                f"What is the fundamental rule behind {weak_prereq_title or target_stage.title}?",
                f"Given a simple test case, how do you verify correctness in {target_stage.title}?"
            ],
            expected_misconceptions=target_stage.expected_misconceptions,
            prerequisite_ids=[],
            next_best_action=NextBestAction.TEACH
        )

        ResourceRecommenderEngine.evaluate_stage_resources(remedial_stage)
        return remedial_stage


class StageOperationsEngine:
    """
    Provides safe, deterministic stage manipulation operations (reorder, merge, split, duplicate).
    """

    @staticmethod
    def reorder_stages(roadmap: LearningRoadmap, stage_ids: List[str]) -> bool:
        id_to_stage = {s.id: s for s in roadmap.stages}
        if len(stage_ids) != len(roadmap.stages) or set(stage_ids) != set(id_to_stage.keys()):
            return False

        reordered = [id_to_stage[sid] for sid in stage_ids]
        for i, s in enumerate(reordered):
            s.sequence = i
        roadmap.stages = reordered
        PrerequisiteEngine.evaluate_readiness(roadmap)
        StateMachineEngine.determine_next_action(roadmap)
        return True

    @staticmethod
    def merge_stages(
        roadmap: LearningRoadmap,
        stage_id_1: str,
        stage_id_2: str,
        new_title: Optional[str] = None
    ) -> Optional[RoadmapStage]:
        s1 = next((s for s in roadmap.stages if s.id == stage_id_1), None)
        s2 = next((s for s in roadmap.stages if s.id == stage_id_2), None)
        if not s1 or not s2:
            return None

        combined_title = new_title or f"{s1.title} & {s2.title}"
        combined_desc = f"{s1.description}\n{s2.description}".strip()
        combined_duration = s1.duration_minutes + s2.duration_minutes
        
        merged = RoadmapStage(
            id=f"merged_{s1.id}_{s2.id}",
            concept_id=s1.concept_id,
            title=combined_title,
            description=combined_desc,
            duration_minutes=combined_duration,
            status=StageStatus.AVAILABLE if s1.status == StageStatus.AVAILABLE or s2.status == StageStatus.AVAILABLE else s1.status,
            objectives=s1.objectives + s2.objectives,
            prerequisite_ids=list(dict.fromkeys(s1.prerequisite_ids + s2.prerequisite_ids)),
            teacher_actions=s1.teacher_actions + s2.teacher_actions,
            student_actions=s1.student_actions + s2.student_actions,
            activities=s1.activities + s2.activities,
            checkpoint_questions=s1.checkpoint_questions + s2.checkpoint_questions,
            expected_misconceptions=s1.expected_misconceptions + s2.expected_misconceptions,
            source_refs=s1.source_refs + s2.source_refs
        )

        idx = min(roadmap.stages.index(s1), roadmap.stages.index(s2))
        roadmap.stages = [s for s in roadmap.stages if s.id not in (stage_id_1, stage_id_2)]
        roadmap.stages.insert(idx, merged)
        
        ResourceRecommenderEngine.evaluate_stage_resources(merged)
        PrerequisiteEngine.evaluate_readiness(roadmap)
        StateMachineEngine.determine_next_action(roadmap)
        return merged

    @staticmethod
    def split_stage(
        roadmap: LearningRoadmap,
        stage_id: str,
        split_title_1: str,
        split_title_2: str,
        duration_1: int,
        duration_2: int
    ) -> Optional[Tuple[RoadmapStage, RoadmapStage]]:
        s = next((st for st in roadmap.stages if st.id == stage_id), None)
        if not s:
            return None

        part1 = RoadmapStage(
            id=f"{s.id}_part1",
            concept_id=f"{s.concept_id}_p1",
            title=split_title_1,
            description=f"Part 1 of {s.title}: {s.description}",
            duration_minutes=duration_1,
            status=s.status,
            prerequisite_ids=s.prerequisite_ids,
            teacher_actions=s.teacher_actions[:len(s.teacher_actions)//2 + 1] if s.teacher_actions else [],
            student_actions=s.student_actions[:len(s.student_actions)//2 + 1] if s.student_actions else [],
            checkpoint_questions=s.checkpoint_questions[:1] if s.checkpoint_questions else [],
            expected_misconceptions=s.expected_misconceptions
        )

        part2 = RoadmapStage(
            id=f"{s.id}_part2",
            concept_id=f"{s.concept_id}_p2",
            title=split_title_2,
            description=f"Part 2 of {s.title}: Application and practice.",
            duration_minutes=duration_2,
            status=StageStatus.LOCKED,
            prerequisite_ids=[part1.concept_id],
            teacher_actions=s.teacher_actions[len(s.teacher_actions)//2 + 1:] if s.teacher_actions else [],
            student_actions=s.student_actions[len(s.student_actions)//2 + 1:] if s.student_actions else [],
            checkpoint_questions=s.checkpoint_questions[1:] if len(s.checkpoint_questions) > 1 else s.checkpoint_questions,
            expected_misconceptions=[]
        )

        ResourceRecommenderEngine.evaluate_stage_resources(part1)
        ResourceRecommenderEngine.evaluate_stage_resources(part2)

        idx = roadmap.stages.index(s)
        roadmap.stages.pop(idx)
        roadmap.stages.insert(idx, part2)
        roadmap.stages.insert(idx, part1)

        PrerequisiteEngine.evaluate_readiness(roadmap)
        StateMachineEngine.determine_next_action(roadmap)
        return part1, part2


class ChangeImpactEngine:
    """
    Analyzes user modifications and deterministically marks downstream resources stale
    without regenerating unrelated stages.
    """

    @staticmethod
    def analyze_stage_modification(
        stage: RoadmapStage,
        changed_fields: List[str]
    ) -> List[ResourceType]:
        """
        Determines which resources become STALE when stage content changes.
        """
        stale_resources: List[ResourceType] = []
        
        if "objectives" in changed_fields or "title" in changed_fields:
            # Major change -> PPT, Quiz, Teach Me become stale
            stale_resources.extend([ResourceType.PPT, ResourceType.QUIZ, ResourceType.TEACH_ME])
        elif "checkpoint_questions" in changed_fields or "expected_misconceptions" in changed_fields:
            # Assessment changed -> Quiz and Teach Me become stale
            stale_resources.extend([ResourceType.QUIZ, ResourceType.TEACH_ME])
        elif "duration_minutes" in changed_fields:
            # Timing changed -> No external resource dependencies
            pass

        for rec in stage.resource_recommendations:
            if rec.resource_type in stale_resources and rec.status == ResourceStatus.READY:
                rec.status = ResourceStatus.STALE

        return stale_resources

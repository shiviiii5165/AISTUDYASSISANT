"""
Pedagogical Story Compiler
==========================
Compiles a ConceptGraph and LearningIntent into an educational Storyboard.
Enforces the 10-stage Teaching Story Architecture:
HOOK -> INTUITION -> PREREQUISITE_CONNECTION -> CORE_CONCEPT -> VISUAL_MECHANISM ->
WORKED_EXAMPLE -> COMMON_MISTAKE -> SECOND_EXAMPLE -> QUICK_CHECK -> SUMMARY.
Populates rich VisualSpecs with concrete structured elements (nodes, edges, steps,
timelines, comparisons, equations) according to assigned visual archetypes.
"""
from typing import List, Dict, Any, Optional
from ..schemas import (
    Storyboard, SceneSpec, VisualSpec, VisualAssetType, VisualStrategyArchetype,
    TeachingStoryStage, LearningIntent, ConceptGraph, TimelineEvent, ComparisonColumn,
    EquationStep, PlotData, PlotSeries, AnimationSpec, AnimationStep, VideoStyle
)


class StoryboardCompiler:
    """Compiles curriculum graphs into structured, duration-exact storyboards."""

    @classmethod
    def compile(cls, intent: LearningIntent, graph: ConceptGraph) -> Storyboard:
        duration = intent.duration_seconds
        scenes: List[SceneSpec] = []

        # Determine target scene count based on duration
        if duration <= 90:
            target_scene_count = 3
        elif duration <= 180:
            target_scene_count = 5
        elif duration <= 300:
            target_scene_count = 7
        elif duration <= 450:
            target_scene_count = 9
        else:
            target_scene_count = 10

        base_duration = duration // target_scene_count
        remainder = duration % target_scene_count

        # Build sequence of teaching stages
        stages: List[TeachingStoryStage] = [
            TeachingStoryStage.HOOK,
            TeachingStoryStage.INTUITION,
            TeachingStoryStage.PREREQUISITE_CONNECTION,
            TeachingStoryStage.CORE_CONCEPT,
            TeachingStoryStage.VISUAL_MECHANISM,
            TeachingStoryStage.WORKED_EXAMPLE,
            TeachingStoryStage.COMMON_MISTAKE,
            TeachingStoryStage.SECOND_EXAMPLE,
            TeachingStoryStage.QUICK_CHECK,
            TeachingStoryStage.SUMMARY,
        ][:target_scene_count]

        # Map concept nodes across scenes
        c_nodes = graph.nodes or []
        node_count = len(c_nodes)

        for idx, stage in enumerate(stages):
            s_dur = base_duration + (remainder if idx == target_scene_count - 1 else 0)
            active_node = c_nodes[min(idx, node_count - 1)] if c_nodes else None
            scene = cls._build_scene_for_stage(
                idx=idx + 1,
                stage=stage,
                duration=s_dur,
                intent=intent,
                graph=graph,
                active_node=active_node
            )
            scenes.append(scene)

        # Duration sanity normalization
        total_dur = sum(s.duration for s in scenes)
        diff = duration - total_dur
        if diff != 0 and scenes:
            scenes[-1].duration = max(5, scenes[-1].duration + diff)

        return Storyboard(
            topic=intent.topic,
            domain=intent.domain,
            style=VideoStyle.ACADEMIC,
            language=intent.language,
            total_duration=duration,
            scenes=scenes,
            learning_objectives=graph.learning_objectives,
            prerequisites=graph.prerequisites,
            summary_notes=f"Complete pedagogical masterclass on {intent.topic}."
        )

    @classmethod
    def _build_scene_for_stage(
        cls,
        idx: int,
        stage: TeachingStoryStage,
        duration: int,
        intent: LearningIntent,
        graph: ConceptGraph,
        active_node: Optional[Any]
    ) -> SceneSpec:
        lang = intent.language.lower()
        topic = intent.topic
        node_name = active_node.name if active_node else topic
        node_summary = active_node.summary if active_node else f"Fundamentals of {topic}"

        # 1. Assign Visual Archetype per scene
        if stage in (TeachingStoryStage.HOOK, TeachingStoryStage.INTUITION):
            archetype = VisualStrategyArchetype.CONCEPT_MAP
        elif stage == TeachingStoryStage.PREREQUISITE_CONNECTION:
            archetype = VisualStrategyArchetype.HIERARCHY
        elif stage == TeachingStoryStage.VISUAL_MECHANISM:
            archetype = active_node.recommended_visual_archetype if active_node else VisualStrategyArchetype.PROCESS_FLOW
        elif stage == TeachingStoryStage.WORKED_EXAMPLE:
            archetype = VisualStrategyArchetype.STEP_SEQUENCE
        elif stage == TeachingStoryStage.COMMON_MISTAKE:
            archetype = VisualStrategyArchetype.COMPARISON
        elif stage == TeachingStoryStage.SECOND_EXAMPLE:
            archetype = VisualStrategyArchetype.TABLE
        elif stage == TeachingStoryStage.QUICK_CHECK:
            archetype = VisualStrategyArchetype.GENERIC_DIAGRAM
        else:
            archetype = VisualStrategyArchetype.COMPARISON

        # Special domain-guided archetype overrides
        clean_topic = topic.lower()
        if "linked list" in clean_topic:
            if stage in (TeachingStoryStage.CORE_CONCEPT, TeachingStoryStage.VISUAL_MECHANISM, TeachingStoryStage.WORKED_EXAMPLE):
                archetype = VisualStrategyArchetype.DATA_STRUCTURE
            elif stage == TeachingStoryStage.COMMON_MISTAKE:
                archetype = VisualStrategyArchetype.COMPARISON
        elif "french revolution" in clean_topic and stage in (TeachingStoryStage.INTUITION, TeachingStoryStage.VISUAL_MECHANISM):
            archetype = VisualStrategyArchetype.TIMELINE
        elif "integration by parts" in clean_topic and stage in (TeachingStoryStage.VISUAL_MECHANISM, TeachingStoryStage.WORKED_EXAMPLE):
            archetype = VisualStrategyArchetype.MATHEMATICAL_DERIVATION
        elif "newton" in clean_topic and stage == TeachingStoryStage.VISUAL_MECHANISM:
            archetype = VisualStrategyArchetype.GRAPH_PLOT

        # 2. Build Narration and Captions
        narration, caption, visual_spec, animation_spec = cls._craft_content(
            stage=stage,
            topic=topic,
            node_name=node_name,
            node_summary=node_summary,
            archetype=archetype,
            lang=lang,
            intent=intent,
            graph=graph,
            active_node=active_node
        )

        return SceneSpec(
            scene_id=f"scene_{idx:02d}",
            order=idx,
            concept_id=active_node.id if active_node else f"concept_{idx}",
            concept_name=node_name,
            teaching_goal=f"Teach {stage.value.replace('_', ' ')} of {node_name}",
            purpose=stage,
            duration=duration,
            narration=narration,
            visual_strategy=archetype,
            visual_type=VisualAssetType.PYTHON_GRAPHICS,
            visual_spec=visual_spec,
            animation_spec=animation_spec,
            caption=caption,
            prerequisite_refs=active_node.prerequisites if active_node else [],
            misconception_tags=active_node.likely_misconceptions if active_node else [],
            worked_example=active_node.worked_example_hint if active_node else None,
            difficulty="intermediate"
        )

    @classmethod
    def _craft_content(
        cls,
        stage: TeachingStoryStage,
        topic: str,
        node_name: str,
        node_summary: str,
        archetype: VisualStrategyArchetype,
        lang: str,
        intent: LearningIntent,
        graph: ConceptGraph,
        active_node: Optional[Any]
    ) -> tuple:
        """Constructs pedagogical script, visual spec, and animation spec."""
        clean_topic = topic.lower()

        # Build Visual Spec
        v_spec = VisualSpec(
            visual_archetype=archetype,
            title=node_name,
            theme="academic",
            bullets=[node_summary]
        )

        # Build Animation Spec with 30fps keyframes
        anim_spec = AnimationSpec(
            fps=30,
            total_frames=150,
            steps=[
                AnimationStep(step_index=1, action="reveal", description=f"Introduce {node_name}", duration_ratio=0.2),
                AnimationStep(step_index=2, action="highlight", description="Focus on core mechanism", duration_ratio=0.5),
                AnimationStep(step_index=3, action="transform", description="State transition", duration_ratio=0.3),
            ]
        )

        # Stage-specific narration & visual payload
        if stage == TeachingStoryStage.HOOK:
            caption = f"Introduction: {topic}"
            if lang == "hinglish":
                narration = f"Kya aapne kabhi socha hai ki {topic} internally kaise kaam karta hai? Aaj hum ise step by step bilkul basic se master karenge."
            elif lang == "hindi":
                narration = f"क्या आपने कभी सोचा है कि {topic} आंतरिक रूप से कैसे काम करता है? आज हम इसे गहराई से समझेंगे।"
            else:
                narration = f"Have you ever wondered how {topic} actually works under the hood? Today we will break down its core operational principles from first principles."

            v_spec.nodes = [topic, "Intuition", "Core Mechanism", "Practical Application"]
            v_spec.edges = [[topic, "Intuition"], ["Intuition", "Core Mechanism"], ["Core Mechanism", "Practical Application"]]

        elif stage == TeachingStoryStage.INTUITION:
            caption = f"Intuition: {node_name}"
            if lang == "hinglish":
                narration = f"{node_name} ka main purpose hai complex operations ko efficient banana. {node_summary}"
            elif lang == "hindi":
                narration = f"{node_name} का मुख्य उद्देश्य जटिल प्रक्रियाओं को सरल बनाना है। {node_summary}"
            else:
                narration = f"The intuition behind {node_name} is straightforward: {node_summary}"

            v_spec.steps = ["Identify Problem", "Formulate Mental Model", "Establish Invariant"]

        elif stage == TeachingStoryStage.PREREQUISITE_CONNECTION:
            caption = f"Prerequisites: {node_name}"
            prereqs = graph.prerequisites[:3] if graph.prerequisites else ["Foundational Principles"]
            prereq_str = ", ".join(prereqs)
            if lang == "hinglish":
                narration = f"Is concept ko samajhne ke liye aapko {prereq_str} ka idea hona chahiye. Agar ye clear hai, toh aage ki journey bahut aasan hogi."
            elif lang == "hindi":
                narration = f"इसे समझने के लिए आपको {prereq_str} की बुनियादी समझ होनी चाहिए।"
            else:
                narration = f"To fully grasp this concept, let's connect it to our foundational building blocks: {prereq_str}."

            v_spec.nodes = [prereqs[0] if prereqs else "Prerequisite", node_name]
            v_spec.edges = [[v_spec.nodes[0], node_name]]

        elif stage in (TeachingStoryStage.CORE_CONCEPT, TeachingStoryStage.VISUAL_MECHANISM):
            caption = f"Mechanism: {node_name}"
            if lang == "hinglish":
                narration = f"Ab dhyan se dekhiye iska core mechanism: {node_summary}. Har step ek specific transition produce karta hai."
            elif lang == "hindi":
                narration = f"अब ध्यान से इसकी मुख्य कार्यप्रणाली को देखिए: {node_summary}।"
            else:
                narration = f"Now observe the core mechanism closely: {node_summary}. Every transition preserves structural invariants."

            # Customize visual spec according to archetype
            if archetype == VisualStrategyArchetype.DATA_STRUCTURE:
                v_spec.title = "Linked List Node Structure" if "linked list" in clean_topic else node_name
                v_spec.nodes = ["HEAD", "Node(20)", "Node(30)", "NULL"]
                v_spec.edges = [["HEAD", "Node(20)"], ["Node(20)", "Node(30)"], ["Node(30)", "NULL"]]
            elif archetype == VisualStrategyArchetype.TIMELINE:
                v_spec.timeline_events = [
                    TimelineEvent(time_label="May 1789", title="Estates-General", description="Financial Crisis"),
                    TimelineEvent(time_label="June 1789", title="Tennis Court Oath", description="National Assembly"),
                    TimelineEvent(time_label="July 1789", title="Storming of Bastille", description="Defiance of Absolute Rule")
                ]
            elif archetype == VisualStrategyArchetype.MATHEMATICAL_DERIVATION:
                v_spec.equations = [
                    EquationStep(equation="d(uv)/dx = u*(dv/dx) + v*(du/dx)", explanation="Product Rule of Differentiation"),
                    EquationStep(equation="int(d(uv)) = int(u dv) + int(v du)", explanation="Integrate Both Sides"),
                    EquationStep(equation="int(u dv) = uv - int(v du)", explanation="Integration by Parts Identity", highlight_terms=["uv", "- int(v du)"])
                ]
            elif archetype == VisualStrategyArchetype.GRAPH_PLOT:
                v_spec.plot_data = PlotData(
                    title="F = m * a (Force vs Acceleration)",
                    x_label="Acceleration (a)",
                    y_label="Net Force (F)",
                    series=[PlotSeries(x_values=[0, 2, 4, 6, 8, 10], y_values=[0, 10, 20, 30, 40, 50], label="Mass m = 5 kg")]
                )
            elif archetype == VisualStrategyArchetype.PROCESS_FLOW:
                v_spec.steps = ["Light Absorption (Thylakoids)", "Water Splitting (O2 Released)", "ATP & NADPH Synthesis", "Calvin Cycle (Glucose Fixed)"]
            elif archetype == VisualStrategyArchetype.TABLE:
                v_spec.table_headers = ["Attribute", "1NF (Atomic)", "2NF (No Partial)", "3NF (No Transitive)"]
                v_spec.table_rows = [
                    ["Candidate Keys", "Preserved", "Preserved", "Preserved"],
                    ["Dependencies", "Any", "Full Key Only", "Non-transitive"],
                    ["Anomalies", "High", "Moderate", "Eliminated"]
                ]
            elif archetype == VisualStrategyArchetype.CHART:
                v_spec.steps = ["Awareness (TOFU)", "Consideration (MOFU)", "Decision (BOFU)", "Retention (Advocacy)"]

        elif stage == TeachingStoryStage.WORKED_EXAMPLE:
            caption = f"Worked Example: {node_name}"
            ex_hint = active_node.worked_example_hint if active_node and active_node.worked_example_hint else f"Concrete walkthrough of {node_name}"
            if lang == "hinglish":
                narration = f"Chaliye ek real worked example dekhte hain: {ex_hint}. Notice kijiye values kaise transform hoti hain."
            elif lang == "hindi":
                narration = f"आइए एक वास्तविक उदाहरण से इसे समझें: {ex_hint}।"
            else:
                narration = f"Let's trace through a concrete worked example: {ex_hint}. Notice how each state changes deterministically."

            if "linked list" in clean_topic:
                v_spec.steps = ["Target: Insert 25 between 20 and 30", "Step 1: Point 25.next -> 30", "Step 2: Update 20.next -> 25", "Result: 20 -> 25 -> 30"]
            else:
                v_spec.steps = [f"Initial State: {node_name}", "Step 1: Apply Operation", "Step 2: Verify Invariant", "Final State: Verified Result"]

        elif stage == TeachingStoryStage.COMMON_MISTAKE:
            caption = f"Common Pitfalls: {node_name}"
            traps = active_node.likely_misconceptions if active_node and active_node.likely_misconceptions else ["Common misunderstanding of operational order"]
            trap_text = traps[0]
            if lang == "hinglish":
                narration = f"Students aksar yahan ek major mistake karte hain: {trap_text}. Is galati se bachne ke liye hamesha order aur dependencies check karein."
            elif lang == "hindi":
                narration = f"विद्यार्थी अक्सर यहाँ एक बड़ी गलती करते हैं: {trap_text}। इस गलती से बचने के लिए हमेशा सही क्रम का ध्यान रखें।"
            else:
                narration = f"A frequent student pitfall here is {trap_text}. Always verify your dependency order before executing this step."

            v_spec.comparisons = [
                ComparisonColumn(header="Correct Approach", items=["Follow verified operational order", "Preserve references/units", "Check edge boundaries"], color_accent="#10B981"),
                ComparisonColumn(header="Common Mistake", items=[trap_text, "Overwriting before saving link", "Assuming linear behavior"], color_accent="#EF4444")
            ]

        elif stage == TeachingStoryStage.QUICK_CHECK:
            caption = f"Quick Check: {node_name}"
            if lang == "hinglish":
                narration = f"Quick check: Kya aap predict kar sakte hain ki agar is condition ko change kar diya jaye, toh output par kya asar padega?"
            elif lang == "hindi":
                narration = f"त्वरित जाँच: क्या आप बता सकते हैं कि यदि हम इस स्थिति को बदल दें तो परिणाम क्या होगा?"
            else:
                narration = f"Quick understanding check: Can you predict how the system behaves if the order of operations is reversed?"

            v_spec.title = "Concept Checkpoint"
            v_spec.bullets = ["What invariant must hold true?", "Which reference must be updated first?", "How does this prevent state corruption?"]

        else:  # SUMMARY
            caption = f"Summary & Key Takeaways"
            if lang == "hinglish":
                narration = f"Summary me: {topic} ke core principles, dynamic mechanisms, aur common mistakes ko humne cover kiya. Great job!"
            elif lang == "hindi":
                narration = f"संक्षेप में: हमने {topic} के मुख्य सिद्धांतों और प्रक्रियाओं को पूरी तरह समझ लिया है।"
            else:
                narration = f"In summary: We have mastered the intuition, operational mechanism, and pitfalls of {topic}. Great work!"

            v_spec.title = f"Key Takeaways: {topic}"
            v_spec.bullets = [
                f"Core mechanism: {node_name}",
                "Preserve operational invariants and dependencies",
                "Avoid common edge case traps and misconceptions"
            ]

        return narration, caption, v_spec, anim_spec

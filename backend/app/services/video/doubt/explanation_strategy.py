"""
Explanation Strategy Engine & Strategy Escalation Tracker
=========================================================
Generates conversational, targeted doubt answers using the exact context of the video.
Never generates another video (Decision #13).
Escalates strategies to ensure a failed explanation is never repeated (Decision #14):
SIMPLE -> VISUAL -> REAL_WORLD_ANALOGY -> STEP_BY_STEP -> PREREQUISITE_REPAIR -> SECOND_EXAMPLE -> COUNTEREXAMPLE.
"""
from typing import List, Dict, Any, Optional
from app.core.logging import logger
from ..schemas import (
    ExplanationStrategy, ConfusionType, DoubtContext, DoubtAnswer, MasteryCheck,
    DoubtTutorResponse
)
from .mastery_check import QuickMasteryCheckGenerator
from app.services.ai import router


# Default escalation sequence if learner remains confused
STRATEGY_ESCALATION_ORDER: List[ExplanationStrategy] = [
    ExplanationStrategy.SIMPLE,
    ExplanationStrategy.VISUAL,
    ExplanationStrategy.REAL_WORLD_ANALOGY,
    ExplanationStrategy.STEP_BY_STEP,
    ExplanationStrategy.PREREQUISITE_REPAIR,
    ExplanationStrategy.SECOND_EXAMPLE,
    ExplanationStrategy.COUNTEREXAMPLE,
    ExplanationStrategy.EXAM_STYLE,
    ExplanationStrategy.CODE_TRACE,
    ExplanationStrategy.FORMULA_BREAKDOWN
]


class ExplanationStrategyEngine:
    """Selects and executes pedagogical explanation strategies without repeating failures (Decision #8 & #14)."""

    @classmethod
    def determine_strategy(
        cls,
        recommended: ExplanationStrategy,
        tried_strategies: List[ExplanationStrategy],
        learner_guidance: Optional[Dict[str, Any]] = None,
    ) -> ExplanationStrategy:
        """
        Picks the next untried strategy in the escalation ladder.
        Adapts based on learner mastery history:
        - If previous strategies failed, strictly avoids them.
        - If learner has a prerequisite gap, prioritizes PREREQUISITE_REPAIR.
        - If learner has repeated confusion, reduces abstraction (favors REAL_WORLD_ANALOGY or STEP_BY_STEP).
        """
        all_avoid = set(tried_strategies)
        if learner_guidance:
            for s_val in learner_guidance.get("avoid_strategies", []):
                try:
                    all_avoid.add(ExplanationStrategy(s_val))
                except Exception:
                    pass

            if learner_guidance.get("inject_prerequisite_repair") and ExplanationStrategy.PREREQUISITE_REPAIR not in all_avoid:
                return ExplanationStrategy.PREREQUISITE_REPAIR

            if learner_guidance.get("reduce_abstraction") and recommended == ExplanationStrategy.SIMPLE:
                if ExplanationStrategy.REAL_WORLD_ANALOGY not in all_avoid:
                    return ExplanationStrategy.REAL_WORLD_ANALOGY
                elif ExplanationStrategy.STEP_BY_STEP not in all_avoid:
                    return ExplanationStrategy.STEP_BY_STEP

        if recommended not in all_avoid:
            return recommended

        # Find next strategy in escalation ladder
        for s in STRATEGY_ESCALATION_ORDER:
            if s not in all_avoid:
                return s

        return ExplanationStrategy.STEP_BY_STEP

    @classmethod
    def escalate_strategy(
        cls,
        previous_strategy: ExplanationStrategy,
        confusion_type: ConfusionType,
        learner_history: List[Any],
    ) -> ExplanationStrategy:
        """Escalates to the next untried pedagogical strategy avoiding previous ones."""
        tried = []
        for s in learner_history:
            try:
                tried.append(ExplanationStrategy(s))
            except Exception:
                pass
        if previous_strategy not in tried:
            tried.append(previous_strategy)
        return cls.determine_strategy(recommended=ExplanationStrategy.STEP_BY_STEP, tried_strategies=tried)


    @classmethod
    async def generate_doubt_answer(
        cls,
        context: DoubtContext,
        confusion_type: ConfusionType,
        strategy: ExplanationStrategy,
        tried_strategies: List[ExplanationStrategy],
        session_history: Optional[List[Any]] = None,
        referential_anchors: Optional[List[Any]] = None,
        use_llm: bool = True,
    ) -> DoubtAnswer:
        """
        Primary LLM Tutor: Synthesizes a tailored, context-specific doubt response
        grounded in active scene visual state, transcript, prerequisites, and conversation history.
        Free-First Routing: Groq -> Gemini -> OpenRouter -> Deterministic Local Fallback.
        """
        question = context.student_question.strip()
        lang = context.language.lower()

        if use_llm and question:
            try:
                # 1. Compile bounded conversation history summary
                history_str = ""
                if session_history:
                    turns_formatted = []
                    for t in session_history[-3:]:
                        q = getattr(t, "user_question", "")
                        ans = getattr(t, "tutor_explanation", "")[:120]
                        strat = getattr(t, "strategy_used", "")
                        turns_formatted.append(f"- Student: '{q}' | Tutor ({strat}): '{ans}...'")
                    if turns_formatted:
                        history_str = "Recent Conversation:\n" + "\n".join(turns_formatted)

                # 2. Compile referential anchors summary
                anchors_str = ""
                if referential_anchors:
                    anchors_formatted = []
                    for a in referential_anchors[:5]:
                        lbl = getattr(a, "label", "")
                        snip = getattr(a, "content_snippet", "")
                        anchors_formatted.append(f"- Anchor: {lbl} (Context: {snip})")
                    if anchors_formatted:
                        anchors_str = "Active Referential Visual & Worked Anchors on Screen:\n" + "\n".join(anchors_formatted)

                prompt_system = f"""You are LearnByGenie's Expert Educational AI Video Tutor.
A learner is watching a video lesson and paused at timestamp {context.timestamp:.1f}s to ask a doubt.

=== PEDAGOGICAL GROUNDING CONTEXT ===
- Lesson Concept: {context.current_concept}
- Learner Level: {context.learner_level}
- Teaching Language: {context.language}
- Active Scene ID: {context.current_scene_id}
- Active Visual Elements on Screen: {getattr(context, 'visual_elements', None) or context.visual_state or 'Educational diagram / whiteboard elements'}
- Worked Example: {getattr(context, 'worked_example', None) or (context.examples_shown[0] if context.examples_shown else 'None')}
- Relevant Video Narration at this moment: "{context.relevant_narration}"
- Foundational Prerequisites: {', '.join(context.prerequisites or ['Core concept foundations'])}
- Known Student Misconceptions: {', '.join(getattr(context, 'misconceptions', None) or context.misconception_tags or ['General ambiguity'])}
- Diagnosed Confusion: {confusion_type.value}
- MANDATORY EXPLANATION STRATEGY TO USE: {strategy.value}

{anchors_str}
{history_str}

=== INSTRUCTIONS ===
1. Address the learner's doubt DIRECTLY, warmly, and with deep pedagogical clarity.
2. Resolve colloquial, deictic, or incomplete follow-ups (e.g. "ye kya hua", "acha 20 wala?", "upar wala", "wahi arrow wala", "exam me kaise likhu", "diagram se bata", "real life example se bata", "still samajh nahi aaya") by grounding in the visual elements and conversation history.
3. STRICTLY execute the requested strategy:
   - SIMPLE: Plain, intuitive explanation without jargon or abstract leaps.
   - VISUAL: Describe the screen visuals, spatial layout, and provide an ASCII/text mini-diagram.
   - REAL_WORLD_ANALOGY: Ground the concept in an intuitive, physical real-world metaphor or story.
   - STEP_BY_STEP: Provide discrete numbered sequential steps showing state before and after.
   - PREREQUISITE_REPAIR: Temporarily review the missing prerequisite before connecting back.
   - COUNTEREXAMPLE: Demonstrate the failure mode or contradiction if the misconception is followed.
   - EXAM_STYLE: Provide a structured, high-scoring exam answer format (Definition, Key Points, Formula/Code).
   - CODE_TRACE: Step-by-step code trace with variable values.
   - FORMULA_BREAKDOWN: Break down every symbol and transformation in the equation.
4. Match teaching language ({context.language}):
   - If Hinglish: Use natural conversational Hindi in Latin script mixed with English technical terms (never translate technical keywords like pointers, nodes, derivatives, ATP, quantum, etc.).
   - If English: Clean, natural educational English.
5. Create ONE targeted interactive concept check question (`mastery_check`) to verify understanding.

You MUST respond in valid JSON format matching this schema:
{{
  "answer": "Complete markdown explanation adhering to the strategy and language",
  "strategy_used": "{strategy.value}",
  "concept_id": "{context.current_concept}",
  "prerequisite_repair_used": null,
  "mini_diagram": null,
  "steps": null,
  "example": null,
  "exam_answer": null,
  "mastery_check": {{
    "question": "Targeted 1-question check",
    "options": ["Option A", "Option B", "Option C", "Option D"],
    "correct_answer_index": 0,
    "explanation": "Why correct",
    "target_concept_id": "{context.current_concept}"
  }},
  "confidence": 0.95,
  "grounded_scene_ids": ["{context.current_scene_id}"]
}}"""

                messages = [
                    {"role": "system", "content": prompt_system},
                    {"role": "user", "content": f"Student Question: {question}"}
                ]

                # Call ModelRouter on free-first task 'doubt_tutor': Groq -> Gemini -> OpenRouter
                raw_json = await router.generate_json(
                    task="doubt_tutor",
                    messages=messages,
                    temperature=0.3,
                    max_tokens=2048,
                    timeout=20.0
                )

                tutor_resp = DoubtTutorResponse.model_validate(raw_json)
                logger.info(f"[DoubtTutorLLM] LLM response generated successfully for strategy '{strategy.value}'")
                return tutor_resp.to_doubt_answer(
                    scene_id=context.current_scene_id or "scene_01",
                    concept_name=context.current_concept,
                    timestamp=context.timestamp,
                    confusion_type=confusion_type
                )
            except Exception as llm_e:
                logger.warning(f"[DoubtTutorLLM] LLM Tutor generation notice ({llm_e}); gracefully falling back to deterministic answer.")

        # Deterministic fallback
        return cls._answer_deterministic(context, confusion_type, strategy, lang)

    @classmethod
    def generate_doubt_answer_sync(
        cls,
        context: DoubtContext,
        confusion_type: ConfusionType,
        strategy: ExplanationStrategy,
        tried_strategies: List[ExplanationStrategy]
    ) -> DoubtAnswer:
        """Synchronous deterministic fallback entrypoint."""
        lang = context.language.lower()
        return cls._answer_deterministic(context, confusion_type, strategy, lang)

    @classmethod
    def _answer_deterministic(
        cls,
        context: DoubtContext,
        confusion_type: ConfusionType,
        strategy: ExplanationStrategy,
        lang: str
    ) -> DoubtAnswer:
        """Deterministic rule-based and canonical domain handlers fallback."""
        question = context.student_question.lower()
        if "20.next" in question or ("25" in question and "linked list" in context.relevant_narration.lower()):
            return cls._answer_linked_list_pointer_insertion(context, strategy, lang)
        elif "minus" in question or ("sign" in question and "integral" in context.relevant_narration.lower()):
            return cls._answer_integration_minus_sign(context, strategy, lang)
        elif "war" in question or "french revolution" in context.relevant_narration.lower() or "bastille" in question:
            return cls._answer_french_revolution_causes(context, strategy, lang)
        elif "atp" in question or "photosynthesis" in context.relevant_narration.lower():
            return cls._answer_photosynthesis_atp(context, strategy, lang)
        else:
            return cls._answer_generic_concept(context, confusion_type, strategy, lang)

    @classmethod
    def _answer_linked_list_pointer_insertion(cls, context: DoubtContext, strategy: ExplanationStrategy, lang: str) -> DoubtAnswer:
        mini_diagram = "20 ──────> 30\n        ▲\n        │ (Step 1: 25.next = 30)\n20 ──> 25 ────> 30  (Step 2: 20.next = 25)"
        step_trace = [
            "Before insertion: 20 was pointing directly to 30 (20 -> 30).",
            "We want to place 25 between them without losing any nodes.",
            "Step 1: Connect 25.next = 30 (preserving reference to remaining chain).",
            "Step 2: Connect 20.next = 25.",
            "Result: 20 -> 25 -> 30.",
            "Why not 20.next first? If we did 20.next = 25 first, our only pointer to 30 would be overwritten, and node 30 would be permanently lost!"
        ]

        if strategy == ExplanationStrategy.REAL_WORLD_ANALOGY:
            md = (
                "### Analogy: Holding Hands in a Human Chain\n\n"
                "Think of 20 and 30 holding hands in a chain: `[20] 🤝 [30]`.\n\n"
                "A friend `[25]` wants to join between them:\n"
                "1. If `[20]` lets go of `[30]` first before `[25]` grasps `[30]`, `[30]` drifts away and is lost in the crowd!\n"
                "2. Therefore, `[25]` must first grab `[30]`'s hand with one hand.\n"
                "3. Once secured, `[20]` can let go of `[30]` and grab `[25]`'s other hand.\n\n"
                "Now everyone remains connected: `[20] 🤝 [25] 🤝 [30]`."
            )
        elif strategy == ExplanationStrategy.VISUAL:
            md = (
                "### Visual Pointer Transition\n\n"
                "```text\n"
                "Initial:\n"
                "[20 | next] ───────────────> [30 | NULL]\n\n"
                "Step 1 (25.next = 20.next):\n"
                "[20 | next] ───────────────> [30 | NULL]\n"
                "                ▲\n"
                "                │\n"
                "[25 | next] ────┘\n\n"
                "Step 2 (20.next = 25):\n"
                "[20 | next] ──> [25 | next] ──> [30 | NULL]\n"
                "```\n\n"
                "Notice that both pointers are never broken at the same time."
            )
        else:
            if lang in ("hinglish", "hindi"):
                md = (
                    "### 20.next ko 25 kyu kiya?\n\n"
                    "Pehele node 20 direct 30 ko point kar raha tha: `20 -> 30`.\n\n"
                    "Hum chahte hain ki **25** unke beech me aa jaye:\n\n"
                    "1. **Pehle Step 1:** Hum `25.next` ko 30 se connect karte hain (`25.next = 20.next`).\n"
                    "2. **Fir Step 2:** Hum `20.next` ko 25 bana dete hain (`20.next = 25`).\n\n"
                    "Ab poori chain jud gayi: **20 → 25 → 30**.\n\n"
                    "> **Agar 20.next pehle change karte toh kya hota?**\n"
                    "> 30 ka address hamesha ke liye kho jaata aur 30 or aage ke saare nodes memory leak ban jaate!"
                )
            else:
                md = (
                    "### Why did we update 20.next to 25?\n\n"
                    "Node 20 was originally pointing directly to node 30 (`20 -> 30`).\n\n"
                    "To insert **25** in between:\n\n"
                    "1. **First:** Link `25.next = 30` so we don't lose the reference to 30.\n"
                    "2. **Second:** Update `20.next = 25` to redirect 20 towards our new node.\n\n"
                    "Now the linked chain is complete: **20 → 25 → 30**.\n\n"
                    "If we changed `20.next` first, our only pointer to 30 would be erased, stranding node 30 in memory."
                )

        check = QuickMasteryCheckGenerator.create_check_for_concept("linked_list_insertion")

        return DoubtAnswer(
            context_scene_id=context.current_scene_id,
            context_concept_name=context.current_concept,
            timestamp=context.timestamp,
            confusion_type=ConfusionType.PROCESS_CONFUSION,
            strategy_used=strategy,
            explanation_markdown=md,
            mini_diagram=mini_diagram,
            step_trace=step_trace,
            mastery_check=check
        )

    @classmethod
    def _answer_integration_minus_sign(cls, context: DoubtContext, strategy: ExplanationStrategy, lang: str) -> DoubtAnswer:
        if lang in ("hinglish", "hindi"):
            md = (
                "### Ye minus sign (-) yaha kaise aaya?\n\n"
                "Ye minus sign **Product Rule of Differentiation** se derive hota hai:\n\n"
                "$$\\frac{d}{dx}(u \\cdot v) = u \\frac{dv}{dx} + v \\frac{du}{dx}$$\n\n"
                "Dono taraf integrate karne par:\n\n"
                "$$u \\cdot v = \\int u \\, dv + \\int v \\, du$$\n\n"
                "Jab hum $\\int u \\, dv$ ko isolate karte hain, toh $\\int v \\, du$ doosri taraf jaakar **subtract** hota hai:\n\n"
                "$$\\int u \\, dv = u \\cdot v - \\int v \\, du$$\n\n"
                "Isliye formula me beech me hamesha **minus sign** hota hai!"
            )
        else:
            md = (
                "### Origin of the Minus Sign in Integration by Parts\n\n"
                "The minus sign originates directly from rearranging the **Product Rule of Differentiation**:\n\n"
                "$$d(uv) = u \\, dv + v \\, du$$\n\n"
                "Integrating both sides gives:\n"
                "$$uv = \\int u \\, dv + \\int v \\, du$$\n\n"
                "Subtracting $\\int v \\, du$ from both sides isolates our target integral:\n"
                "$$\\int u \\, dv = uv - \\int v \\, du$$\n\n"
                "The minus sign is simply the consequence of algebraic transposition."
            )

        check = QuickMasteryCheckGenerator.create_check_for_concept("integration_by_parts")
        return DoubtAnswer(
            context_scene_id=context.current_scene_id,
            context_concept_name=context.current_concept,
            timestamp=context.timestamp,
            confusion_type=ConfusionType.FORMULA_CONFUSION,
            strategy_used=strategy,
            explanation_markdown=md,
            mastery_check=check
        )

    @classmethod
    def _answer_french_revolution_causes(cls, context: DoubtContext, strategy: ExplanationStrategy, lang: str) -> DoubtAnswer:
        if lang in ("hinglish", "hindi"):
            md = (
                "### Ye French Revolution start kyu hui?\n\n"
                "Iske peeche 3 main reasons the:\n\n"
                "1. **Bhari Social Inequity (The 3 Estates):** 98% aabadi (Third Estate) saara tax deti thi, jabki amir Clergy aur Nobility bilkul tax nahi dete the.\n"
                "2. **Desh ka Bankruptcy:** France ne American Revolution me itna kharch kar diya tha ki khazana khali ho gaya tha.\n"
                "3. **Famine & Bread Shortage:** 1788-1789 me fasal kharab hui, bread ke prices aasmaan choone lage, aur log bhukhe marne lage.\n\n"
                "Jab King Louis XVI ne tax aur badhane ke liye Estates-General bulayi, toh Third Estate ne National Assembly banakar Bastille par hamla kar diya!"
            )
        else:
            md = (
                "### Why did the French Revolution Begin?\n\n"
                "The revolution was triggered by three intersecting systemic crises:\n\n"
                "1. **Social Inequality (The Three Estates):** The First Estate (Clergy) and Second Estate (Nobility) enjoyed tax exemptions and feudal privileges, while the Third Estate (98% of people) carried 100% of the tax burden.\n"
                "2. **State Insolvency:** France was virtually bankrupt from financing the American Revolution and aristocratic excesses.\n"
                "3. **Severe Bread Famine:** Crop failures in 1788–1789 sent food prices soaring, sparking urban bread riots.\n\n"
                "When King Louis XVI convened the Estates-General to levy new taxes, the Third Estate formed the National Assembly and seized the Bastille on July 14, 1789."
            )

        check = QuickMasteryCheckGenerator.create_check_for_concept("french_revolution")
        return DoubtAnswer(
            context_scene_id=context.current_scene_id,
            context_concept_name=context.current_concept,
            timestamp=context.timestamp,
            confusion_type=ConfusionType.RELATIONSHIP_CONFUSION,
            strategy_used=strategy,
            explanation_markdown=md,
            mastery_check=check
        )

    @classmethod
    def _answer_photosynthesis_atp(cls, context: DoubtContext, strategy: ExplanationStrategy, lang: str) -> DoubtAnswer:
        if lang in ("hinglish", "hindi"):
            md = (
                "### ATP yahan kyu ban raha hai?\n\n"
                "Photosynthesis me sunlight se direct glucose nahi banta!\n\n"
                "1. **Pehle Sunlight energy ko temporarily store kiya jata hai:** Thylakoid membranes me electrons pump hote hain aur **ATP** tatha **NADPH** bante hain.\n"
                "2. **Fir ye ATP Stroma me jati hai:** Jahan Calvin Cycle me CO2 ko jodkar glucose banane ke liye energy provide karti hai.\n\n"
                "> **Key Point:** ATP ek **energy rechargeable battery** ki tarah kaam karti hai jo light reaction ki power ko dark reaction tak pahunchati hai!"
            )
        else:
            md = (
                "### Why is ATP Synthesized in Photosynthesis?\n\n"
                "Sunlight cannot directly fuse carbon dioxide molecules into glucose.\n\n"
                "1. **Light-Dependent Stage (Thylakoids):** Photons energize electrons, generating a proton gradient that ATP synthase uses to produce **ATP and NADPH**.\n"
                "2. **Calvin Cycle (Stroma):** This stored chemical energy in ATP powers RuBisCO and the carbon-reduction enzymes to synthesize sugar (G3P/glucose).\n\n"
                "ATP acts as the indispensable energy carrier between the light and dark reactions."
            )

        check = QuickMasteryCheckGenerator.create_check_for_concept("photosynthesis")
        return DoubtAnswer(
            context_scene_id=context.current_scene_id,
            context_concept_name=context.current_concept,
            timestamp=context.timestamp,
            confusion_type=ConfusionType.PROCESS_CONFUSION,
            strategy_used=strategy,
            explanation_markdown=md,
            mastery_check=check
        )

    @classmethod
    def _answer_generic_concept(cls, context: DoubtContext, confusion_type: ConfusionType, strategy: ExplanationStrategy, lang: str) -> DoubtAnswer:
        concept = context.current_concept
        narration = context.relevant_narration

        if strategy == ExplanationStrategy.REAL_WORLD_ANALOGY:
            md = (
                f"### Real-World Analogy for {concept}\n\n"
                f"Think of **{concept}** like a relay race: every step has a single handover point where control and state are transferred deterministically.\n\n"
                f"In the video at this timestamp, the key point is: *\"{narration}\"*."
            )
        elif strategy == ExplanationStrategy.STEP_BY_STEP:
            md = (
                f"### Step-by-Step Breakdown: {concept}\n\n"
                f"1. **Baseline State:** Observe the initial parameters shown on screen.\n"
                f"2. **Operational Action:** {narration}\n"
                f"3. **Outcome:** The system reaches an updated stable state without breaking invariant constraints."
            )
        else:
            md = (
                f"### Understanding {concept}\n\n"
                f"At this part of the lesson, we are looking at **{concept}**.\n\n"
                f"**Core Intuition:** {narration}\n\n"
                f"- **Why this matters:** It guarantees that dependencies and conditions remain valid throughout the process."
            )

        return DoubtAnswer(
            context_scene_id=context.current_scene_id,
            context_concept_name=concept,
            timestamp=context.timestamp,
            confusion_type=confusion_type,
            strategy_used=strategy,
            explanation_markdown=md
        )

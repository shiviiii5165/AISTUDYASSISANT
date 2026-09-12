"""
Pedagogy Policy Engine for Lesson Planner VNext
===============================================
Maps academic subject domain, teaching intent, and concept type to
concrete pedagogical stage sequences with active instructional actions.

Pedagogy Policy Rules (Section 12):
1. Fact / definition: Recall → Example → Retrieval
2. Conceptual: Prior Knowledge → Mental Model → Analogy → Misconception → Application
3. Procedure: Demonstration → Worked Example → Guided Practice → Independent Practice
4. Mathematics: Intuition → Representation → Derivation → Worked Example → Misconception Check → Independent Problem
5. Coding: Problem → Concept → Visualization → Pseudocode → Code → Debugging → Practice
6. Engineering: Physical Intuition → Model → Equations → System Diagram → Worked Application → Simulation
7. Research: Background → Seminal Work → Literature Landscape → Current Methods → Conflicting Evidence → Gaps
"""

from enum import Enum
from typing import List, Dict, Any, Tuple
from pydantic import BaseModel, Field

from ..schemas import (
    StageArchetype, CanonicalDomain, TeachingIntent
)


class ConceptType(str, Enum):
    FACT_DEFINITION = "fact_definition"
    CONCEPTUAL = "conceptual"
    PROCEDURAL = "procedural"
    MATHEMATICS = "mathematics"
    CODING = "coding"
    ENGINEERING = "engineering"
    RESEARCH = "research"


class StageTemplate(BaseModel):
    archetype: StageArchetype
    default_duration_pct: float  # Percentage of total lesson time
    pedagogy_goal: str
    suggested_teacher_action: str
    suggested_student_action: str
    requires_visual: bool = False
    requires_coding_env: bool = False
    requires_scholarly_refs: bool = False


class PedagogyPolicyEngine:
    """
    Pure Python deterministic engine for pedagogical sequence synthesis.
    Zero LLM arithmetic.
    """

    @classmethod
    def detect_concept_type(
        cls,
        topic: str,
        domain: CanonicalDomain,
        intent: TeachingIntent
    ) -> ConceptType:
        """
        Deterministically resolves the concept type based on domain and intent.
        """
        # 1. Research intent always takes research pedagogy
        if intent == TeachingIntent.RESEARCH:
            return ConceptType.RESEARCH

        # 2. Coding / CS domains with implementation/practice/interview intent
        if domain in [CanonicalDomain.COMPUTER_SCIENCE, CanonicalDomain.SOFTWARE_ENGINEERING]:
            if intent in [TeachingIntent.IMPLEMENT, TeachingIntent.PRACTICE, TeachingIntent.INTERVIEW_PREP, TeachingIntent.PROJECT]:
                return ConceptType.CODING
            lower = topic.lower()
            if any(k in lower for k in ["code", "programming", "implementation", "recursion", "traversal", "search", "sort", "stack", "tree"]):
                return ConceptType.CODING

        # 3. Mathematics
        if domain == CanonicalDomain.MATHEMATICS:
            return ConceptType.MATHEMATICS

        # 4. Engineering / ECE / Electrical
        if domain in [CanonicalDomain.ECE, CanonicalDomain.ELECTRICAL]:
            return ConceptType.ENGINEERING

        # 5. Definitions / Intro
        if intent == TeachingIntent.INTRODUCE:
            return ConceptType.FACT_DEFINITION

        # 6. Default to rich Conceptual topic
        return ConceptType.CONCEPTUAL

    @classmethod
    def get_pedagogy_templates(cls, concept_type: ConceptType) -> List[StageTemplate]:
        """
        Returns the structured sequence of archetypes and actions for the concept type.
        """
        if concept_type == ConceptType.CODING:
            return [
                StageTemplate(
                    archetype=StageArchetype.HOOK,
                    default_duration_pct=0.10,
                    pedagogy_goal="Problem definition & real-world motivation",
                    suggested_teacher_action="Presents a concrete real-world computational problem with an inefficient baseline",
                    suggested_student_action="Identifies why naive approach fails or has unacceptable time complexity",
                    requires_visual=False
                ),
                StageTemplate(
                    archetype=StageArchetype.MENTAL_MODEL,
                    default_duration_pct=0.20,
                    pedagogy_goal="Concept & structural visualization",
                    suggested_teacher_action="Illustrates the data structures and state transitions step-by-step with visual diagrams",
                    suggested_student_action="Traces pointer transitions or state changes on paper",
                    requires_visual=True
                ),
                StageTemplate(
                    archetype=StageArchetype.DEMONSTRATION,
                    default_duration_pct=0.25,
                    pedagogy_goal="Pseudocode to canonical code implementation",
                    suggested_teacher_action="Live codes clean implementation, highlighting invariant conditions and base cases",
                    suggested_student_action="Reconstructs core loop condition and writes matching edge-case test inputs",
                    requires_coding_env=True
                ),
                StageTemplate(
                    archetype=StageArchetype.GUIDED_PRACTICE,
                    default_duration_pct=0.25,
                    pedagogy_goal="Guided debugging & pattern variations",
                    suggested_teacher_action="Introduces subtle off-by-one or boundary defect for active debugging",
                    suggested_student_action="Executes dry run, diagnoses bug, and writes correct fix",
                    requires_coding_env=True
                ),
                StageTemplate(
                    archetype=StageArchetype.DIAGNOSTIC_CHECK,
                    default_duration_pct=0.20,
                    pedagogy_goal="Independent practice & complexity check",
                    suggested_teacher_action="Launches 2-problem formative check and analyzes student error patterns",
                    suggested_student_action="Solves independent practice problem and explains Big-O runtime",
                    requires_coding_env=True
                )
            ]

        elif concept_type == ConceptType.MATHEMATICS:
            return [
                StageTemplate(
                    archetype=StageArchetype.HOOK,
                    default_duration_pct=0.15,
                    pedagogy_goal="Intuition & physical meaning",
                    suggested_teacher_action="Demonstrates the geometric or physical interpretation before formal symbols",
                    suggested_student_action="Visualizes representation and sketches intuitive meaning",
                    requires_visual=True
                ),
                StageTemplate(
                    archetype=StageArchetype.CONCEPT_INTRO,
                    default_duration_pct=0.25,
                    pedagogy_goal="Formal representation & derivation",
                    suggested_teacher_action="Derives the governing equation step-by-step, explaining each mathematical step",
                    suggested_student_action="Follows derivation line-by-line and identifies critical algebraic transformation",
                    requires_visual=False
                ),
                StageTemplate(
                    archetype=StageArchetype.WORKED_EXAMPLE,
                    default_duration_pct=0.25,
                    pedagogy_goal="Canonical worked example with common misconception check",
                    suggested_teacher_action="Walks through representative standard problem and flags common arithmetic/sign pitfalls",
                    suggested_student_action="Computes intermediate values alongside instructor",
                    requires_visual=False
                ),
                StageTemplate(
                    archetype=StageArchetype.INDEPENDENT_PRACTICE,
                    default_duration_pct=0.20,
                    pedagogy_goal="Independent problem solving",
                    suggested_teacher_action="Assigns varied numerical or analytical problem set with graded difficulty",
                    suggested_student_action="Solves independent problem without hints and validates solution",
                    requires_visual=False
                ),
                StageTemplate(
                    archetype=StageArchetype.DIAGNOSTIC_CHECK,
                    default_duration_pct=0.15,
                    pedagogy_goal="Formative checkpoint & misconception test",
                    suggested_teacher_action="Polls class with targeted conceptual diagnostic item",
                    suggested_student_action="Selects correct reasoning and refutes distractor misconceptions",
                    requires_visual=False
                )
            ]

        elif concept_type == ConceptType.RESEARCH:
            return [
                StageTemplate(
                    archetype=StageArchetype.HOOK,
                    default_duration_pct=0.15,
                    pedagogy_goal="Problem motivation & seminal foundation",
                    suggested_teacher_action="Presents the foundational bottleneck and landmark seminal paper",
                    suggested_student_action="Examines seminal assumptions and historical limitations",
                    requires_scholarly_refs=True
                ),
                StageTemplate(
                    archetype=StageArchetype.RESEARCH_REVIEW,
                    default_duration_pct=0.30,
                    pedagogy_goal="Literature landscape & taxonomy of methods",
                    suggested_teacher_action="Surveys Q1/A* peer-reviewed literature across competing paradigms",
                    suggested_student_action="Compares algorithmic tradeoffs and empirical benchmark claims",
                    requires_scholarly_refs=True
                ),
                StageTemplate(
                    archetype=StageArchetype.CASE_STUDY,
                    default_duration_pct=0.30,
                    pedagogy_goal="Deep-dive into frontier state-of-the-art",
                    suggested_teacher_action="Deconstructs latest high-impact paper methodology, datasets, and ablation results",
                    suggested_student_action="Critically analyzes experimental validity and conflicting evidence",
                    requires_scholarly_refs=True
                ),
                StageTemplate(
                    archetype=StageArchetype.DISCUSSION,
                    default_duration_pct=0.25,
                    pedagogy_goal="Open research gaps & future extensions",
                    suggested_teacher_action="Moderates structured discussion on unsolved bottlenecks and open problems",
                    suggested_student_action="Formulates a testable research hypothesis addressing identified gap",
                    requires_scholarly_refs=True
                )
            ]

        # Standard Conceptual Topic (Default)
        return [
            StageTemplate(
                archetype=StageArchetype.HOOK,
                default_duration_pct=0.15,
                pedagogy_goal="Real-world curiosity hook & prior knowledge activation",
                suggested_teacher_action="Presents an anomaly or intriguing dilemma that cannot be explained with prior knowledge",
                suggested_student_action="Proposes initial hypotheses and discovers limitations of naive thinking",
                requires_visual=True
            ),
            StageTemplate(
                archetype=StageArchetype.MENTAL_MODEL,
                default_duration_pct=0.30,
                pedagogy_goal="Mental model, analogy & core principles",
                suggested_teacher_action="Builds the conceptual mental model using a vivid analogy and clear system diagram",
                suggested_student_action="Maps the elements of the analogy to the actual system components",
                requires_visual=True
            ),
            StageTemplate(
                archetype=StageArchetype.WORKED_EXAMPLE,
                default_duration_pct=0.25,
                pedagogy_goal="Concrete demonstration with preemptive misconception check",
                suggested_teacher_action="Applies core principles to a standard scenario while explicitly dissecting common misconception",
                suggested_student_action="Identifies why the common misconception leads to an incorrect conclusion",
                requires_visual=False
            ),
            StageTemplate(
                archetype=StageArchetype.GUIDED_PRACTICE,
                default_duration_pct=0.15,
                pedagogy_goal="Guided application & peer discussion",
                suggested_teacher_action="Facilitates paired think-pair-share problem solving with targeted hints",
                suggested_student_action="Collaborates with peer to solve applied scenario and justify reasoning",
                requires_visual=False
            ),
            StageTemplate(
                archetype=StageArchetype.DIAGNOSTIC_CHECK,
                default_duration_pct=0.15,
                pedagogy_goal="Formative diagnostic checkpoint",
                suggested_teacher_action="Administers 2-question checkpoint and verifies class-wide readiness",
                suggested_student_action="Submits responses and reviews immediate diagnostic feedback",
                requires_visual=False
            )
        ]

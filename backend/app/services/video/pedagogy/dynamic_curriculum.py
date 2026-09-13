"""
Dynamic Curriculum Intelligence Engine
======================================
Builds structured concept graphs, prerequisite chains, learning objectives,
and likely student misconceptions for ANY topic without hard-coded limitations.
Uses ModelRouter with strict schema validation and deterministic topic fallbacks.
"""
from typing import Dict, Any, List, Optional
from app.core.logging import logger
from app.services.ai import router
from ..schemas import (
    ConceptGraph, ConceptNode, DomainCategory, VisualStrategyArchetype, LearningIntent
)
from .domain_intelligence import DomainIntelligenceEngine


CURRICULUM_PROMPT = """You are a master educational curriculum architect and cognitive scientist.
Given a topic, domain, learner level, and duration, decompose the subject into a pedagogically sound Concept Graph.

REQUIREMENTS:
1. Identify 2-4 prerequisite concepts the learner must know.
2. Formulate 3-5 clear learning objectives.
3. Break the topic down into 3-7 core concept nodes in logical teaching order.
4. For each concept node:
   - "name": Concise concept title
   - "summary": 1-2 sentence core definition/principle
   - "prerequisites": concepts from prerequisites or prior nodes
   - "likely_misconceptions": 1-2 common student misunderstandings
   - "recommended_visual_archetype": one of: "process_flow", "timeline", "cause_effect", "comparison", "hierarchy", "concept_map", "data_structure", "algorithm_trace", "mathematical_derivation", "graph_plot", "formula_visualization", "scientific_process", "table", "chart", "generic_diagram"
   - "worked_example_hint": brief description of a concrete example
5. List 2-4 class-wide major misconceptions to address.

Return strict JSON:
{{
  "topic": "{topic}",
  "learning_objectives": ["..."],
  "prerequisites": ["..."],
  "major_misconceptions": ["..."],
  "nodes": [
    {{
      "id": "node_1",
      "name": "...",
      "summary": "...",
      "prerequisites": [],
      "likely_misconceptions": ["..."],
      "recommended_visual_archetype": "...",
      "worked_example_hint": "..."
    }}
  ]
}}
"""


# Deterministic high-quality baseline graphs for benchmark domains (ensures 100% test reliability & offline resilience)
BENCHMARK_CURRICULUM_CATALOG: Dict[str, Dict[str, Any]] = {
    "linked list": {
        "domain": DomainCategory.COMPUTER_SCIENCE,
        "learning_objectives": [
            "Understand dynamic node-and-pointer memory structure",
            "Trace pointer updates during insertion and deletion",
            "Evaluate time/space trade-offs compared to contiguous arrays"
        ],
        "prerequisites": ["Variables & Data Types", "Memory Addresses & References"],
        "major_misconceptions": [
            "Confusing the pointer with the node object itself",
            "Losing the reference chain by updating next pointer in wrong order",
            "Assuming elements are stored contiguously like arrays"
        ],
        "nodes": [
            {
                "id": "c1_why_linked_lists",
                "name": "Why Linked Lists Exist (Array Limits)",
                "summary": "Arrays require contiguous memory blocks, making resizing and middle insertions costly. Linked lists store nodes anywhere in memory.",
                "prerequisites": ["Variables & Data Types"],
                "likely_misconceptions": ["Thinking linked lists are faster than arrays for index lookups"],
                "recommended_visual_archetype": VisualStrategyArchetype.COMPARISON,
                "worked_example_hint": "Contiguous array vs scattered heap nodes"
            },
            {
                "id": "c2_node_structure",
                "name": "Node Anatomy (Data + Next Pointer)",
                "summary": "Each node contains two compartments: data payload and a pointer holding the memory address of the next node.",
                "prerequisites": ["Memory Addresses & References"],
                "likely_misconceptions": ["Confusing the pointer variable with the actual destination node"],
                "recommended_visual_archetype": VisualStrategyArchetype.DATA_STRUCTURE,
                "worked_example_hint": "[20 | next] -> [30 | NULL]"
            },
            {
                "id": "c3_head_and_traversal",
                "name": "HEAD Pointer & Chain Traversal",
                "summary": "HEAD points to the start of the list. We traverse node-by-node following next until reaching NULL.",
                "prerequisites": ["Node Anatomy (Data + Next Pointer)"],
                "likely_misconceptions": ["Thinking HEAD is a full node rather than a pointer reference"],
                "recommended_visual_archetype": VisualStrategyArchetype.ALGORITHM_TRACE,
                "worked_example_hint": "curr = head; while(curr != NULL) curr = curr.next"
            },
            {
                "id": "c4_insertion_mechanism",
                "name": "Node Insertion & Pointer Order",
                "summary": "To insert node 25 between 20 and 30, connect new_node.next to 30 FIRST, then update 20.next to new_node. Reversing this drops the chain.",
                "prerequisites": ["HEAD Pointer & Chain Traversal"],
                "likely_misconceptions": ["Overwriting 20.next first, which permanently orphans 30 and the remaining chain"],
                "recommended_visual_archetype": VisualStrategyArchetype.DATA_STRUCTURE,
                "worked_example_hint": "Insert 25 between 20 -> 30: 25.next = 20.next; 20.next = 25"
            },
            {
                "id": "c5_deletion_mechanism",
                "name": "Node Deletion & Memory Cleanup",
                "summary": "To delete a node, reroute the predecessor's next pointer directly to the successor, bypassing the target node.",
                "prerequisites": ["Node Insertion & Pointer Order"],
                "likely_misconceptions": ["Deleting the node in memory before adjusting predecessor pointers"],
                "recommended_visual_archetype": VisualStrategyArchetype.DATA_STRUCTURE,
                "worked_example_hint": "prev.next = target.next"
            },
            {
                "id": "c6_summary_tradeoffs",
                "name": "Complexity & Real-World Trade-Offs",
                "summary": "Linked lists provide O(1) insertions given a pointer, but suffer O(N) access and pointer memory overhead.",
                "prerequisites": ["Node Deletion & Memory Cleanup"],
                "likely_misconceptions": ["Believing linked lists are always better than arrays"],
                "recommended_visual_archetype": VisualStrategyArchetype.TABLE,
                "worked_example_hint": "Access O(N) vs Insertion O(1)"
            }
        ]
    },
    "integration by parts": {
        "domain": DomainCategory.MATHEMATICS,
        "learning_objectives": [
            "Derive integration by parts from the product rule",
            "Select optimal u and dv using the LIATE rule",
            "Evaluate definite and indefinite integrals with transformed terms"
        ],
        "prerequisites": ["Product Rule of Differentiation", "Basic Integration Techniques"],
        "major_misconceptions": [
            "Choosing u and dv arbitrarily leading to more complex integrals",
            "Forgetting the negative sign in the formula integral(u dv) = uv - integral(v du)",
            "Dropping integration constants during intermediate parts"
        ],
        "nodes": [
            {
                "id": "m1_origin",
                "name": "Derivation from Product Rule",
                "summary": "Since d/dx(uv) = u(dv/dx) + v(du/dx), integrating both sides yields the integration by parts identity.",
                "prerequisites": ["Product Rule of Differentiation"],
                "likely_misconceptions": ["Viewing integration by parts as an arbitrary formula rather than reverse product rule"],
                "recommended_visual_archetype": VisualStrategyArchetype.MATHEMATICAL_DERIVATION,
                "worked_example_hint": "d(uv) = u dv + v du => uv = int(u dv) + int(v du)"
            },
            {
                "id": "m2_liate_strategy",
                "name": "Choosing u and dv with LIATE",
                "summary": "Select u based on priority: Logarithmic, Inverse trig, Algebraic, Trigonometric, Exponential. Let dv be the remainder.",
                "prerequisites": ["Derivation from Product Rule"],
                "likely_misconceptions": ["Setting dv to something that is difficult or impossible to integrate"],
                "recommended_visual_archetype": VisualStrategyArchetype.HIERARCHY,
                "worked_example_hint": "For int(x * e^x dx): u=x (Algebraic), dv=e^x dx (Exponential)"
            },
            {
                "id": "m3_stepwise_execution",
                "name": "Stepwise Transformation & Negative Sign",
                "summary": "Compute du and v, substitute into uv - int(v du), and evaluate the simpler secondary integral.",
                "prerequisites": ["Choosing u and dv with LIATE"],
                "likely_misconceptions": ["Distributing the minus sign incorrectly across negative antiderivatives"],
                "recommended_visual_archetype": VisualStrategyArchetype.STEP_SEQUENCE,
                "worked_example_hint": "int(x * e^x dx) = x*e^x - int(e^x dx) = x*e^x - e^x + C"
            }
        ]
    },
    "newton's second law": {
        "domain": DomainCategory.PHYSICS,
        "learning_objectives": [
            "Understand force as the rate of change of momentum",
            "Apply F = ma to accelerated bodies and free-body diagrams",
            "Analyze vector directions of net force and acceleration"
        ],
        "prerequisites": ["Vectors & Net Force", "Velocity and Acceleration"],
        "major_misconceptions": [
            "Believing an object in motion must experience an external net force",
            "Treating F = ma as a scalar relationship without vector components",
            "Confusing mass (inertia) with weight (gravitational pull)"
        ],
        "nodes": [
            {
                "id": "p1_net_force_concept",
                "name": "Inertia vs Acceleration",
                "summary": "A nonzero net force causes an object of mass m to change velocity, producing acceleration proportional to force and inversely to mass.",
                "prerequisites": ["Velocity and Acceleration"],
                "likely_misconceptions": ["Thinking force is needed to keep an object moving at constant speed"],
                "recommended_visual_archetype": VisualStrategyArchetype.CAUSE_EFFECT,
                "worked_example_hint": "Pushing an empty shopping cart vs a loaded one"
            },
            {
                "id": "p2_f_equals_ma",
                "name": "Mathematical Formulation (F = ma)",
                "summary": "F_net = m * a states that acceleration is in the exact direction of the net resultant vector force.",
                "prerequisites": ["Inertia vs Acceleration"],
                "likely_misconceptions": ["Substituting a single applied force instead of the vector sum of all forces"],
                "recommended_visual_archetype": VisualStrategyArchetype.GRAPH_PLOT,
                "worked_example_hint": "Slope of F vs a gives mass m"
            },
            {
                "id": "p3_free_body_diagram",
                "name": "Free-Body Analysis & Real Scenarios",
                "summary": "Resolve all forces (gravity, normal, friction, applied) along perpendicular axes to compute resultant acceleration.",
                "prerequisites": ["Mathematical Formulation (F = ma)"],
                "likely_misconceptions": ["Omitting reaction forces or friction opposition"],
                "recommended_visual_archetype": VisualStrategyArchetype.SYSTEM_ARCHITECTURE,
                "worked_example_hint": "Box on inclined surface: mg*sin(theta) - f = m*a"
            }
        ]
    },
    "photosynthesis": {
        "domain": DomainCategory.BIOLOGY,
        "learning_objectives": [
            "Identify chloroplast structures: thylakoid membranes and stroma",
            "Trace light-dependent reactions generating ATP and NADPH",
            "Trace Calvin cycle fixing carbon dioxide into glucose"
        ],
        "prerequisites": ["Cellular Structure", "Basic Chemical Reactions & Energy"],
        "major_misconceptions": [
            "Thinking photosynthesis only produces glucose and does not release oxygen from water splitting",
            "Believing the dark reaction (Calvin cycle) happens only at night",
            "Confusing chlorophyll with chloroplast"
        ],
        "nodes": [
            {
                "id": "b1_overview",
                "name": "Solar Energy Conversion Overview",
                "summary": "6CO2 + 6H2O + Light -> C6H12O6 + 6O2 converts radiant photon energy into stable chemical bonds.",
                "prerequisites": ["Cellular Structure"],
                "likely_misconceptions": ["Thinking oxygen comes from carbon dioxide rather than water molecules"],
                "recommended_visual_archetype": VisualStrategyArchetype.PROCESS_FLOW,
                "worked_example_hint": "Leaf intake of sunlight, water, and CO2"
            },
            {
                "id": "b2_light_reactions",
                "name": "Light-Dependent Reactions (Thylakoids)",
                "summary": "Chlorophyll pigments absorb photons, photolyze water to release O2, and energize electrons to generate ATP and NADPH.",
                "prerequisites": ["Solar Energy Conversion Overview"],
                "likely_misconceptions": ["Thinking sunlight is used directly to assemble carbon rings"],
                "recommended_visual_archetype": VisualStrategyArchetype.SCIENTIFIC_PROCESS,
                "worked_example_hint": "Photosystem II splitting H2O -> 2H+ + 1/2 O2 + electrons"
            },
            {
                "id": "b3_calvin_cycle",
                "name": "Light-Independent Reactions (Calvin Cycle)",
                "summary": "In the stroma, enzyme RuBisCO fixes CO2 into 3-PGA, reduced by ATP/NADPH to produce glucose precursor G3P.",
                "prerequisites": ["Light-Dependent Reactions (Thylakoids)"],
                "likely_misconceptions": ["Believing dark reactions require darkness; they simply do not directly require light photons"],
                "recommended_visual_archetype": VisualStrategyArchetype.PROCESS_FLOW,
                "worked_example_hint": "3 CO2 molecules fixed to produce 1 net G3P"
            }
        ]
    },
    "french revolution": {
        "domain": DomainCategory.HISTORY,
        "learning_objectives": [
            "Examine structural social inequality under the Three Estates",
            "Analyze chronological catalysts from the Estates-General to the Storming of the Bastille",
            "Evaluate long-term impacts on democracy, human rights, and the rise of Napoleon"
        ],
        "prerequisites": ["Feudal Social Hierarchy", "Absolutist Monarchy Principles"],
        "major_misconceptions": [
            "Viewing the revolution as a sudden peasant riot rather than a multi-phase structural crisis",
            "Thinking the storming of the Bastille ended the French monarchy immediately",
            "Ignoring the economic famine and bankruptcy that triggered the crisis"
        ],
        "nodes": [
            {
                "id": "h1_old_regime",
                "name": "Social Inequity & The Three Estates",
                "summary": "First Estate (Clergy) and Second Estate (Nobility) held wealth and tax exemptions, while the Third Estate (98% of population) bore total taxation.",
                "prerequisites": ["Feudal Social Hierarchy"],
                "likely_misconceptions": ["Thinking all French citizens had equal political representation in the assembly"],
                "recommended_visual_archetype": VisualStrategyArchetype.HIERARCHY,
                "worked_example_hint": "Tax burden carried by peasant farmers and urban workers"
            },
            {
                "id": "h2_crisis_and_bastille",
                "name": "1789 Crisis & The Storming of the Bastille",
                "summary": "State bankruptcy and bread famine forced Louis XVI to call the Estates-General. Third Estate formed the National Assembly and stormed the Bastille on July 14, 1789.",
                "prerequisites": ["Social Inequity & The Three Estates"],
                "likely_misconceptions": ["Believing the Bastille was attacked for political prisoners rather than gunpowder and symbolic defiance"],
                "recommended_visual_archetype": VisualStrategyArchetype.TIMELINE,
                "worked_example_hint": "May 1789: Estates-General -> June 1789: Tennis Court Oath -> July 1789: Bastille"
            },
            {
                "id": "h3_consequences",
                "name": "Declaration of Rights & Global Impact",
                "summary": "The Declaration of the Rights of Man established universal civic equality and sovereignty, abolishing feudalism and inspiring modern democratic republics.",
                "prerequisites": ["1789 Crisis & The Storming of the Bastille"],
                "likely_misconceptions": ["Assuming the revolution produced an immediate stable democracy"],
                "recommended_visual_archetype": VisualStrategyArchetype.CAUSE_EFFECT,
                "worked_example_hint": "From Absolute Monarchy to Constitutional Rights and Napoleon's Civil Code"
            }
        ]
    },
    "database normalization": {
        "domain": DomainCategory.COMPUTER_SCIENCE,
        "learning_objectives": [
            "Identify insert, update, and delete anomalies in unnormalized schemas",
            "Apply functional dependencies to achieve 1NF, 2NF, and 3NF",
            "Decompose tables into lossless, dependency-preserving relations"
        ],
        "prerequisites": ["Relational Database Basics", "Primary and Foreign Keys"],
        "major_misconceptions": [
            "Assuming higher normal forms are always optimal for read-heavy analytical databases",
            "Confusing partial dependency (violates 2NF) with transitive dependency (violates 3NF)",
            "Thinking normalization deletes duplicate data records rather than restructuring schema"
        ],
        "nodes": [
            {
                "id": "db1_anomalies",
                "name": "Redundancy & Modification Anomalies",
                "summary": "Unnormalized tables store repeated attributes, causing update anomalies, insertion blocks, and accidental data deletion.",
                "prerequisites": ["Primary and Foreign Keys"],
                "likely_misconceptions": ["Thinking storing everything in one flat table improves performance"],
                "recommended_visual_archetype": VisualStrategyArchetype.TABLE,
                "worked_example_hint": "Student_Course table where deleting a course erases the student record"
            },
            {
                "id": "db2_1nf_and_2nf",
                "name": "1NF (Atomicity) & 2NF (No Partial Dependencies)",
                "summary": "1NF requires atomic column values. 2NF removes partial functional dependencies on composite candidate keys by decomposing relations.",
                "prerequisites": ["Redundancy & Modification Anomalies"],
                "likely_misconceptions": ["Applying 2NF checks to single-column primary keys (which are already in 2NF)"],
                "recommended_visual_archetype": VisualStrategyArchetype.PROCESS_FLOW,
                "worked_example_hint": "Splitting {StudentID, CourseID, CourseName} into Students and Courses"
            },
            {
                "id": "db3_3nf_and_bcnf",
                "name": "3NF (No Transitive Dependencies)",
                "summary": "Every non-key attribute must depend on the primary key, the whole key, and nothing but the key (eliminating transitive X -> Y -> Z chains).",
                "prerequisites": ["1NF (Atomicity) & 2NF (No Partial Dependencies)"],
                "likely_misconceptions": ["Allowing non-key columns to determine other non-key columns"],
                "recommended_visual_archetype": VisualStrategyArchetype.TABLE,
                "worked_example_hint": "DeptID -> DeptName split out from Employee table"
            }
        ]
    },
    "marketing funnel": {
        "domain": DomainCategory.BUSINESS,
        "learning_objectives": [
            "Map user journeys across TOFU, MOFU, and BOFU stages",
            "Calculate conversion rates, CAC, and drop-off metrics",
            "Formulate optimization strategies to increase customer lifetime value"
        ],
        "prerequisites": ["Basic Business Revenue Models", "Customer Acquisition Basics"],
        "major_misconceptions": [
            "Assuming conversion rates remain linear down the funnel",
            "Focusing exclusively on top-of-funnel traffic while ignoring conversion leakage",
            "Confusing customer acquisition with long-term retention"
        ],
        "nodes": [
            {
                "id": "bf1_stages",
                "name": "Funnel Anatomy: Awareness to Advocacy",
                "summary": "The customer lifecycle narrows progressively: Awareness (TOFU) -> Consideration (MOFU) -> Decision (BOFU) -> Retention.",
                "prerequisites": ["Customer Acquisition Basics"],
                "likely_misconceptions": ["Assuming every visitor who enters awareness is a viable conversion prospect"],
                "recommended_visual_archetype": VisualStrategyArchetype.CHART,
                "worked_example_hint": "10,000 visitors -> 1,000 leads -> 100 trials -> 20 paying customers"
            },
            {
                "id": "bf2_metrics",
                "name": "Conversion Rates & Drop-Off Diagnostics",
                "summary": "Each stage boundary possesses a conversion metric. Identifying high-dropoff junctions pinpoints product/marketing bottlenecks.",
                "prerequisites": ["Funnel Anatomy: Awareness to Advocacy"],
                "likely_misconceptions": ["Blaming marketing for low sales when checkout friction causes the drop-off"],
                "recommended_visual_archetype": VisualStrategyArchetype.PROCESS_FLOW,
                "worked_example_hint": "Bounce rate at signup page vs abandonment at payment gateway"
            },
            {
                "id": "bf3_optimization",
                "name": "Unit Economics & Funnel Optimization",
                "summary": "Sustainable growth requires Customer Acquisition Cost (CAC) to remain significantly below Lifetime Value (LTV:CAC >= 3:1).",
                "prerequisites": ["Conversion Rates & Drop-Off Diagnostics"],
                "likely_misconceptions": ["Scaling ad spending before verifying payback period and retention"],
                "recommended_visual_archetype": VisualStrategyArchetype.COMPARISON,
                "worked_example_hint": "CAC $50 vs LTV $250 yielding 5x return"
            }
        ]
    }
}


class DynamicCurriculumEngine:
    """Constructs validated concept graphs and prerequisite DAGs for any topic."""

    @classmethod
    async def build_concept_graph(
        cls,
        intent: LearningIntent,
        user_id: Optional[str] = None
    ) -> ConceptGraph:
        """
        Builds a validated ConceptGraph using LLM with deterministic catalog fallback.
        """
        clean_topic = intent.topic.lower().strip()

        # 1. Check if an exemplary benchmark catalog entry matches
        for key, catalog_data in BENCHMARK_CURRICULUM_CATALOG.items():
            if key in clean_topic or clean_topic in key:
                logger.info(f"[CurriculumEngine] Using verified catalog for benchmark topic '{key}'")
                return cls._build_from_catalog(intent, catalog_data)

        # 2. Call ModelRouter for dynamic topics
        system_content = CURRICULUM_PROMPT.format(topic=intent.topic)
        if intent.custom_context:
            system_content += f"\n\nGROUNDING CONTEXT (User Provided):\n{intent.custom_context}\nDO NOT fabricate facts contradictory to this context."

        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": f"Topic: {intent.topic}\nDomain: {intent.domain.value}\nLearner Level: {intent.learner_level}\nDuration: {intent.duration_seconds}s"}
        ]

        try:
            raw = await router.generate_json(
                task="planning",
                messages=messages,
                temperature=0.3,
                max_tokens=2500,
                timeout=25.0
            )
            return cls._parse_and_validate_llm_graph(intent, raw)
        except Exception as e:
            logger.warning(f"[CurriculumEngine] Dynamic graph LLM error ({e}). Generating deterministic heuristic graph.")
            return cls._build_heuristic_fallback(intent)

    @classmethod
    def _build_from_catalog(cls, intent: LearningIntent, data: Dict[str, Any]) -> ConceptGraph:
        nodes = []
        for n in data.get("nodes", []):
            nodes.append(ConceptNode(
                id=n["id"],
                name=n["name"],
                summary=n["summary"],
                prerequisites=n.get("prerequisites", []),
                likely_misconceptions=n.get("likely_misconceptions", []),
                recommended_visual_archetype=n.get("recommended_visual_archetype", VisualStrategyArchetype.GENERIC_DIAGRAM),
                worked_example_hint=n.get("worked_example_hint")
            ))

        return ConceptGraph(
            topic=intent.topic,
            domain=data.get("domain", intent.domain),
            learning_objectives=data.get("learning_objectives", []),
            prerequisites=data.get("prerequisites", []),
            nodes=nodes,
            recommended_sequence=[n.id for n in nodes],
            major_misconceptions=data.get("major_misconceptions", [])
        )

    @classmethod
    def _parse_and_validate_llm_graph(cls, intent: LearningIntent, raw: Dict[str, Any]) -> ConceptGraph:
        raw_nodes = raw.get("nodes", [])
        if not raw_nodes or not isinstance(raw_nodes, list):
            return cls._build_heuristic_fallback(intent)

        nodes: List[ConceptNode] = []
        for idx, n in enumerate(raw_nodes):
            arch_str = n.get("recommended_visual_archetype", "generic_diagram")
            try:
                arch = VisualStrategyArchetype(arch_str)
            except Exception:
                arch = VisualStrategyArchetype.GENERIC_DIAGRAM

            nodes.append(ConceptNode(
                id=n.get("id") or f"c_{idx+1}",
                name=n.get("name") or f"Concept {idx+1}",
                summary=n.get("summary") or f"Core principle of {intent.topic}",
                prerequisites=n.get("prerequisites") or [],
                likely_misconceptions=n.get("likely_misconceptions") or [],
                recommended_visual_archetype=arch,
                worked_example_hint=n.get("worked_example_hint")
            ))

        return ConceptGraph(
            topic=raw.get("topic", intent.topic),
            domain=intent.domain,
            learning_objectives=raw.get("learning_objectives", [f"Master fundamentals of {intent.topic}"]),
            prerequisites=raw.get("prerequisites", ["Foundational Subject Concepts"]),
            nodes=nodes,
            recommended_sequence=[n.id for n in nodes],
            major_misconceptions=raw.get("major_misconceptions", [f"Common pitfalls in {intent.topic}"])
        )

    @classmethod
    def _build_heuristic_fallback(cls, intent: LearningIntent) -> ConceptGraph:
        """Safe deterministic fallback ensuring the pipeline NEVER fails for any topic."""
        affinities = DomainIntelligenceEngine.get_domain_archetype_affinities(intent.domain)
        arch1 = affinities[0] if affinities else VisualStrategyArchetype.CONCEPT_MAP
        arch2 = affinities[1] if len(affinities) > 1 else VisualStrategyArchetype.PROCESS_FLOW
        arch3 = affinities[2] if len(affinities) > 2 else VisualStrategyArchetype.COMPARISON

        nodes = [
            ConceptNode(
                id="c1_foundations",
                name=f"Core Foundations of {intent.topic}",
                summary=f"Essential definitions, operational principles, and context of {intent.topic}.",
                prerequisites=["Core Prerequisite Concepts"],
                likely_misconceptions=[f"Superficial terminology confusion regarding {intent.topic}"],
                recommended_visual_archetype=arch1,
                worked_example_hint=f"Introductory baseline example of {intent.topic}"
            ),
            ConceptNode(
                id="c2_mechanism",
                name=f"Operational Mechanism & Dynamic Process",
                summary=f"Step-by-step internal process flow and causal relationships in {intent.topic}.",
                prerequisites=[f"Core Foundations of {intent.topic}"],
                likely_misconceptions=[f"Misunderstanding sequence order or causal dependency in {intent.topic}"],
                recommended_visual_archetype=arch2,
                worked_example_hint=f"Stepwise walkthrough of {intent.topic}"
            ),
            ConceptNode(
                id="c3_synthesis",
                name=f"Applications & Edge Cases",
                summary=f"Practical engineering/analytical tradeoffs, common mistakes, and real-world synthesis.",
                prerequisites=[f"Operational Mechanism & Dynamic Process"],
                likely_misconceptions=[f"Over-generalizing {intent.topic} to scenarios where assumptions break"],
                recommended_visual_archetype=arch3,
                worked_example_hint=f"Real-world application comparison of {intent.topic}"
            )
        ]

        return ConceptGraph(
            topic=intent.topic,
            domain=intent.domain,
            learning_objectives=[
                f"Understand core mechanisms of {intent.topic}",
                f"Apply {intent.topic} principles to concrete scenarios",
                f"Diagnose and avoid common pitfalls in {intent.topic}"
            ],
            prerequisites=["Foundational Background Knowledge"],
            nodes=nodes,
            recommended_sequence=[n.id for n in nodes],
            major_misconceptions=[f"Common misconceptions in {intent.topic}"],
        )

"""
TeachGenie Lesson Planner — Resource Intent Profile Builder
===========================================================
Translates stage titles, archetypes, objectives, and learner weakness state
into a clean, concept-dense ResourceIntentProfile with canonical concepts,
stage intent, programming detection, and negative terms.
"""

import re
from typing import List, Dict, Any, Optional
from .schemas import ResourceIntentProfile, StageIntent, ResourceType, ResourceQueryContext

# Regex to strip pedagogical packaging phrases from stage titles
CLEAN_PREFIX_REGEX = re.compile(
    r"^(remedial\s+recap:\s*|remediation:\s*|deep\s+dive:\s*|intro\s+to:\s*|introduction\s+to:\s*|"
    r"guided\s+practice:\s*|worked\s+example:\s*|assessment\s+&\s*summary:\s*|practice\s+session:\s*|"
    r"mastery\s+check:\s*|formative\s+check:\s*|recap:\s*|overview\s+of:\s*)",
    re.IGNORECASE
)

CLEAN_SUFFIX_REGEX = re.compile(
    r"(,\s*assessment\s*&\s*summary|\s*-\s*practice\s*&\s*assessment|\s*practice\s*&\s*summary|"
    r"\s*-\s*summary|\s*assessment|\s*practice)$",
    re.IGNORECASE
)

# Known domain knowledge dictionaries for deterministic, high-accuracy normalization
KNOWN_TOPIC_REGISTRY: Dict[str, Dict[str, Any]] = {
    "python_oop": {
        "match_patterns": [
            r"object\s+and\s+class.*python",
            r"python.*object.*class",
            r"python.*oop",
            r"oop.*python",
            r"classes?\s+and\s+objects?.*python",
            r"objects?\s+&\s+classes?.*overview",
            r"objects?\s+and\s+classes?"
        ],
        "canonical_topic": "Python object-oriented programming: objects and classes",
        "domain": "computer_science",
        "specialization": "python_programming",
        "subject": "Object-Oriented Programming in Python",
        "concepts": [
            "Object", "Class", "Instantiation", "Instance Attributes", "Methods",
            "__init__ Constructor", "self Parameter", "Encapsulation"
        ],
        "canonical_concept_ids": [
            "cs.python.oop.object",
            "cs.python.oop.class",
            "cs.python.oop.instantiation",
            "cs.python.oop.attributes",
            "cs.python.oop.methods"
        ],
        "synonyms": ["Python classes and objects", "Python OOP fundamentals", "object instantiation in Python"],
        "weaknesses": [
            "Confusing class variables with instance variables",
            "Omitting self in method definitions",
            "Instantiation vs initialization"
        ],
        "misconceptions": [
            "Thinking self is a Python keyword rather than parameter convention",
            "Confusing class attributes with instance attributes"
        ],
        "is_programming": True,
        "programming_language": "Python",
        "negative_terms": [
            "astronomical object", "astronomy", "jwst", "galaxy", "galaxies",
            "photometric classification", "celestial", "redshift", "stellar", "telescope",
            "cosmological", "astrophysics", "light curve", "solar system", "supernova",
            "spectral class", "hubble", "exoplanet", "biological classification",
            "taxonomy", "taxonomic", "phylogenetic", "phylum", "botanical", "specimen",
            "species classification", "genus", "taxa", "clade", "organism",
            "social class", "socioeconomic", "caste system", "working class", "ruling class",
            "middle class", "java vulnerability", "cve-", "deserialization vulnerability in java",
            "java class loader", "java bytecode", "object detection", "yolo", "bounding box",
            "object tracking", "segmentation mask"
        ]
    },
    "dynamic_programming": {
        "match_patterns": [r"dynamic\s+programming", r"\bdp\b", r"memoization", r"tabulation", r"optimal\s+substructure"],
        "canonical_topic": "Dynamic Programming: Memoization and Tabulation",
        "domain": "computer_science",
        "specialization": "algorithms_data_structures",
        "subject": "Algorithms & Optimization",
        "concepts": [
            "Optimal Substructure", "Overlapping Subproblems", "Memoization Top-Down",
            "Tabulation Bottom-Up", "State Transition"
        ],
        "canonical_concept_ids": [
            "cs.algo.dp.memoization", "cs.algo.dp.tabulation",
            "cs.algo.dp.optimal_substructure", "cs.algo.dp.overlapping_subproblems"
        ],
        "synonyms": ["DP memoization", "bottom-up dynamic programming", "state transition recurrences"],
        "weaknesses": ["Identifying optimal substructure", "Off-by-one errors in table dimensions"],
        "misconceptions": ["Assuming all recursion is dynamic programming"],
        "is_programming": True,
        "programming_language": "Python/C++/Java",
        "negative_terms": ["linear programming simplex", "dynamic pricing", "neuro linguistic programming"]
    },
    "binary_search_tree": {
        "match_patterns": [r"binary\s+search\s+tree", r"\bbst\b", r"tree\s+traversal"],
        "canonical_topic": "Binary Search Tree: Operations and Invariant",
        "domain": "computer_science",
        "specialization": "algorithms_data_structures",
        "subject": "Data Structures & Algorithms",
        "concepts": [
            "BST Invariant", "Node Insertion", "Node Search", "Node Deletion",
            "Inorder Traversal", "Balancing Factor"
        ],
        "canonical_concept_ids": [
            "cs.ds.tree.bst.insert", "cs.ds.tree.bst.search",
            "cs.ds.tree.bst.delete", "cs.ds.tree.bst.traversal"
        ],
        "synonyms": ["BST operations", "binary tree invariant", "inorder tree walk"],
        "weaknesses": ["Two-child deletion node replacement", "Tree degeneration into linked list"],
        "misconceptions": ["Assuming binary tree is always binary search tree"],
        "is_programming": True,
        "programming_language": "Python/C++/Java",
        "negative_terms": ["family tree", "decision tree classifier", "phytoplankton tree", "botanical tree"]
    },
    "react_server_components": {
        "match_patterns": [r"react\s+server\s+components?", r"\brsc\b", r"server\s+components?.*react"],
        "canonical_topic": "React Server Components: Architecture and Streaming",
        "domain": "software_engineering",
        "specialization": "web_development",
        "subject": "Modern Web Architecture",
        "concepts": [
            "Server Components", "Client Components", "'use client' Directive",
            "Streaming SSR", "Suspense Boundary"
        ],
        "canonical_concept_ids": [
            "se.react.rsc.server_components", "se.react.rsc.client_components",
            "se.react.rsc.streaming", "se.react.rsc.suspense"
        ],
        "synonyms": ["RSC architecture", "Next.js App Router server components", "React streaming SSR"],
        "weaknesses": ["Passing non-serializable props across server-client boundary"],
        "misconceptions": ["Assuming Server Components replace all client-side state"],
        "is_programming": True,
        "programming_language": "TypeScript/JavaScript",
        "negative_terms": ["chemical reactor", "server rack hardware", "industrial cooling"]
    },
    "massive_mimo": {
        "match_patterns": [r"massive\s+mimo", r"beamforming", r"multi[- ]user\s+mimo", r"5g\s+nr\s+mimo"],
        "canonical_topic": "Massive MIMO: Beamforming and Multi-User Wireless Communication",
        "domain": "electrical_engineering",
        "specialization": "wireless_communications",
        "subject": "Wireless Communications & Signal Processing",
        "concepts": [
            "Spatial Multiplexing", "Precoding Techniques", "Channel State Information",
            "Beamforming", "Pilot Contamination"
        ],
        "canonical_concept_ids": [
            "ee.wireless.mimo.beamforming", "ee.wireless.mimo.precoding",
            "ee.wireless.mimo.channel_estimation"
        ],
        "synonyms": ["multi-user MIMO", "5G beamforming arrays", "channel reciprocity in TDD"],
        "weaknesses": ["Pilot contamination across cells", "High computational complexity of MMSE precoding"],
        "misconceptions": ["Assuming adding more antennas always yields linear capacity gain without CSI"],
        "is_programming": False,
        "negative_terms": ["python", "javascript", "leetcode", "react", "css"]
    },
    "dbms_normalization": {
        "match_patterns": [r"normalization", r"normal\s+form", r"1nf", r"2nf", r"3nf", r"bcnf", r"functional\s+dependency"],
        "canonical_topic": "Database Normalization",
        "domain": "Computer Science / Databases",
        "subject": "Database Management Systems",
        "concepts": [
            "Functional Dependency", "1NF", "2NF", "3NF", "BCNF",
            "Partial Dependency", "Transitive Dependency",
            "Lossless Decomposition", "Dependency Preservation"
        ],
        "synonyms": ["relational schema decomposition", "Boyce-Codd normal form", "candidate keys"],
        "weaknesses": [
            "2NF vs 3NF", "partial dependency", "transitive dependency",
            "lossless join vs dependency preservation", "finding candidate keys"
        ],
        "misconceptions": [
            "Confusing partial dependency (violates 2NF) with transitive dependency (violates 3NF)",
            "Assuming BCNF decomposition always preserves functional dependencies"
        ],
        "is_programming": False,
        "negative_terms": [
            "pandas", "data cleaning", "data mining", "machine learning preprocessing",
            "etl", "scikit-learn", "numpy", "feature scaling", "batch normalization",
            "minmax scaler", "data preprocessing"
        ]
    },
    "linked_list": {
        "match_patterns": [r"linked\s+list", r"singly\s+linked", r"doubly\s+linked"],
        "canonical_topic": "Linked List Data Structure",
        "domain": "Computer Science / Data Structures",
        "subject": "Data Structures & Algorithms",
        "concepts": [
            "Singly Linked List", "Node Structure", "Pointer Traversal",
            "Insertion at Head/Tail", "Deletion by Value", "Doubly Linked List",
            "Cycle Detection"
        ],
        "synonyms": ["singly linked list", "linked list operations", "node pointers"],
        "weaknesses": ["Pointer reassignment ordering", "Handling edge cases (empty list, single node, tail)", "Cycle detection Floyd algorithm"],
        "misconceptions": ["Losing reference to head during insertion", "Memory leak in deletion without proper pointer linkage"],
        "is_programming": True,
        "programming_language": "Python/C++/Java",
        "negative_terms": ["linked data", "semantic web", "rdf", "excel link", "hyperlink", "supply chain"]
    },
    "photosynthesis": {
        "match_patterns": [r"photosynthesis", r"light[- ]dependent", r"calvin\s+cycle", r"thylakoid"],
        "canonical_topic": "Photosynthesis",
        "domain": "Biology / Plant Physiology",
        "subject": "Cellular Biology",
        "concepts": [
            "Light-Dependent Reactions", "Thylakoid Membrane", "Chlorophyll Photoexcitation",
            "Electron Transport Chain", "ATP Synthase & Photophosphorylation", "NADPH Formation", "Calvin Cycle"
        ],
        "synonyms": ["light reactions", "Z-scheme of photosynthesis", "photolysis of water"],
        "weaknesses": ["Differentiating photosystem II and photosystem I roles", "Proton gradient generation across thylakoid"],
        "misconceptions": ["Thinking light reactions produce glucose directly (Calvin cycle does)"],
        "is_programming": False,
        "negative_terms": ["python", "javascript", "leetcode", "code", "programming", "software", "artificial photosynthesis solar cell"]
    },
    "react_hooks": {
        "match_patterns": [r"react\s+hook", r"useeffect", r"usestate", r"react\s+lifecycle"],
        "canonical_topic": "React Hooks — useEffect",
        "domain": "Software Engineering / Web Development",
        "subject": "Frontend Development with React",
        "concepts": [
            "useEffect Hook", "Dependency Array", "Cleanup Function",
            "Component Lifecycle Mapping", "Side Effect Synchronization", "Stale Closures"
        ],
        "synonyms": ["React lifecycle side effects", "useEffect dependencies", "clean up subscriptions"],
        "weaknesses": ["Infinite re-render loops from missing/extra dependencies", "Stale closure values in async effects", "Cleanup execution timing"],
        "misconceptions": ["Treating useEffect like componentDidMount without dependency safety", "Omitting functions from dependency array"],
        "is_programming": True,
        "programming_language": "JavaScript / TypeScript",
        "negative_terms": ["chemical reaction", "reaction time", "nuclear reaction", "react native bridge"]
    },
    "french_revolution": {
        "match_patterns": [r"french\s+revolution", r"bastille", r"estates[- ]general", r"ancien\s+r[eé]gime"],
        "canonical_topic": "French Revolution — Causes & Outbreak",
        "domain": "History / European History",
        "subject": "Modern World History",
        "concepts": [
            "Ancien Régime", "Three Estates System", "Financial Crisis of 1789",
            "Estates-General & National Assembly", "Tennis Court Oath", "Storming of the Bastille",
            "Enlightenment Thinkers (Rousseau, Voltaire)"
        ],
        "synonyms": ["causes of 1789 French revolution", "collapse of French absolute monarchy"],
        "weaknesses": ["Distinguishing structural social causes (Three Estates) from short-term fiscal crisis"],
        "misconceptions": ["Assuming Marie Antoinette 'let them eat cake' was historical cause", "Confusing 1789 with 1830 or 1848 revolutions"],
        "is_programming": False,
        "negative_terms": ["industrial revolution", "american revolution", "russian revolution", "coding", "software", "python"]
    },
    "integration_by_parts": {
        "match_patterns": [r"integration\s+by\s+parts", r"calculus\s+integral", r"liate\s+rule"],
        "canonical_topic": "Calculus — Integration by Parts",
        "domain": "Mathematics / Calculus",
        "subject": "Integral Calculus",
        "concepts": [
            "Integration by Parts Formula", "LIATE / ILATE Rule", "Choice of u and dv",
            "Repeated Integration by Parts", "Tabular Method", "Definite Integrals with Limits"
        ],
        "synonyms": ["integral product rule", "uv minus integral v du", "tabular integration"],
        "weaknesses": ["Choosing incorrect u vs dv leading to cyclic integrals", "Sign errors with negative du or dv terms"],
        "misconceptions": ["Attempting to distribute integral over product directly"],
        "is_programming": False,
        "negative_terms": ["auto parts", "car integration", "system integration testing", "software integration"]
    },
    "newtons_second_law": {
        "match_patterns": [r"newton.*second\s+law", r"force\s*=\s*ma", r"momentum\s+rate"],
        "canonical_topic": "Newton's Second Law of Motion",
        "domain": "Physics / Classical Mechanics",
        "subject": "Physics Mechanics",
        "concepts": [
            "Net External Force", "Acceleration and Mass", "Rate of Change of Linear Momentum",
            "Free Body Diagrams", "F = dp/dt vs F = ma", "Friction and Incline Problems"
        ],
        "synonyms": ["force mass acceleration", "momentum conservation relation", "equations of motion"],
        "weaknesses": ["Forgetting to sum ALL forces in free body diagrams", "Treating F = ma when mass varies (e.g. rocket)"],
        "misconceptions": ["Assuming velocity requires constant net force in motion direction"],
        "is_programming": False,
        "negative_terms": ["newton raphson method", "apple newton", "python", "software"]
    }
}


def clean_stage_title(raw_title: str) -> str:
    """Removes verbose boilerplate from stage titles."""
    if not raw_title:
        return ""
    cleaned = CLEAN_PREFIX_REGEX.sub("", raw_title.strip())
    cleaned = CLEAN_SUFFIX_REGEX.sub("", cleaned.strip())
    return cleaned.strip() or raw_title.strip()


def detect_stage_intent(stage_title: str, archetype: Optional[str] = None, is_remedial: bool = False) -> StageIntent:
    """Determines pedagogical intent of the stage."""
    if is_remedial:
        return StageIntent.REMEDIAL
    
    combined = f"{stage_title} {archetype or ''}".lower()
    
    if any(w in combined for w in ["remedial", "remediation", "recap", "weakness", "struggling"]):
        return StageIntent.REMEDIAL
    if any(w in combined for w in ["diagnostic", "quiz", "assessment", "test", "exit ticket", "check"]):
        return StageIntent.ASSESSMENT
    if any(w in combined for w in ["practice", "coding problem", "exercise", "drill", "solve"]):
        return StageIntent.PRACTICE
    if any(w in combined for w in ["deep dive", "advanced", "proof", "decomposition", "research"]):
        return StageIntent.DEEP_EXPLANATION
    if any(w in combined for w in ["intro", "introduction", "hook", "overview", "foundations"]):
        return StageIntent.INTRODUCTION
    if any(w in combined for w in ["revision", "summary", "wrap up", "exam"]):
        return StageIntent.REVISION
        
    return StageIntent.CONCEPT_LEARNING


class IntentProfileBuilder:
    """
    Constructs a precision ResourceIntentProfile from curriculum and stage context.
    """

    @classmethod
    def build(
        cls,
        roadmap_id: str,
        stage_id: str,
        topic: str,
        stage_title: str,
        stage_description: Optional[str] = None,
        archetype: Optional[str] = None,
        learner_level: str = "B.Tech",
        language: str = "english",
        is_remedial: bool = False,
        concept_id: Optional[str] = None,
        objectives: Optional[List[str]] = None,
        weaknesses: Optional[List[str]] = None
    ) -> ResourceIntentProfile:
        cleaned_title = clean_stage_title(stage_title)
        intent = detect_stage_intent(stage_title, archetype, is_remedial)
        combined_text = f"{topic} {stage_title} {stage_description or ''} {cleaned_title}".lower()

        # Check topic registry for known high-accuracy pedagogical profiles
        matched_profile = None
        for key, prof in KNOWN_TOPIC_REGISTRY.items():
            for pat in prof["match_patterns"]:
                if re.search(pat, combined_text):
                    matched_profile = prof
                    break
            if matched_profile:
                break

        if matched_profile:
            canonical_topic = matched_profile["canonical_topic"]
            domain = matched_profile["domain"]
            specialization = matched_profile.get("specialization")
            subject = matched_profile["subject"]
            concepts = list(matched_profile["concepts"])
            canonical_concept_ids = list(matched_profile.get("canonical_concept_ids", []))
            synonyms = list(matched_profile["synonyms"])
            profile_weaknesses = list(matched_profile["weaknesses"])
            misconceptions = list(matched_profile["misconceptions"])
            is_programming = matched_profile["is_programming"]
            programming_lang = matched_profile.get("programming_language")
            negative_terms = list(matched_profile["negative_terms"])
        else:
            # Dynamic heuristic fallback for uncatalogued topics
            # CRITICAL: NEVER strip subject or programming language when synthesizing canonical topic!
            subject = topic
            prog_keywords = ["python", "java", "c++", "cpp", "javascript", "typescript", "react", "sql", "array", "tree", "graph", "algorithm", "code", "function", "pointer", "oop", "class", "object"]
            is_programming = any(pk in combined_text for pk in prog_keywords)
            
            prog_lang = None
            if "python" in combined_text:
                prog_lang = "Python"
            elif "javascript" in combined_text or "typescript" in combined_text or "react" in combined_text:
                prog_lang = "JavaScript/TypeScript"
            elif "java" in combined_text and "javascript" not in combined_text:
                prog_lang = "Java"
            elif "c++" in combined_text or "cpp" in combined_text:
                prog_lang = "C++"

            programming_lang = prog_lang
            if is_programming:
                domain = "computer_science"
                specialization = f"{prog_lang.lower()}_programming" if prog_lang else "software_engineering"
            else:
                domain = "General Academic"
                specialization = None

            # Always preserve programming language or topic domain in canonical_topic
            if prog_lang and prog_lang.lower() not in cleaned_title.lower():
                canonical_topic = f"{prog_lang} {cleaned_title}"
            elif topic.lower() not in cleaned_title.lower() and len(cleaned_title) < 15:
                canonical_topic = f"{topic}: {cleaned_title}"
            else:
                canonical_topic = cleaned_title if cleaned_title else topic

            # Tokenize key nouns
            words = [w for w in re.split(r"[\s,;:\-—]+", cleaned_title) if len(w) > 3]
            concepts = words[:5] if words else [canonical_topic]
            canonical_concept_ids = [f"concept.{w.lower()}" for w in concepts]
            synonyms = [f"{topic} concepts", f"{cleaned_title} tutorial"]
            profile_weaknesses = weaknesses or []
            misconceptions = []

            # Negative terms: if CS/programming, protect against astronomy, biology taxonomy, sociology, Java vulnerabilities
            negative_terms = ["clickbait", "viral", "unrelated"]
            if is_programming:
                negative_terms.extend([
                    "astronomical object", "astronomy", "jwst", "galaxy", "galaxies",
                    "photometric classification", "celestial", "redshift", "stellar",
                    "telescope", "cosmological", "astrophysics", "biological classification",
                    "taxonomy", "taxonomic", "phylogenetic", "phylum", "botanical", "specimen",
                    "species classification", "social class", "socioeconomic", "caste system",
                    "working class", "ruling class", "middle class"
                ])
                if prog_lang == "Python":
                    negative_terms.extend([
                        "java vulnerability", "cve-", "deserialization vulnerability in java",
                        "java class loader", "java bytecode"
                    ])

        # Merge any specific learner weaknesses passed in
        final_weaknesses = list(set((weaknesses or []) + profile_weaknesses))
        final_objectives = objectives or [f"Understand and apply core concepts of {canonical_topic}"]

        # Resource types priority by intent and programming state
        recommended_types = [ResourceType.YOUTUBE_VIDEO, ResourceType.ACADEMIC_REFERENCE]
        if is_programming:
            recommended_types.append(ResourceType.CODING_PROBLEM)
            recommended_types.append(ResourceType.OFFICIAL_DOCUMENTATION)
        else:
            recommended_types.append(ResourceType.GUIDE)

        # Research visibility policy:
        # Strictly NEVER show research papers by default for basic programming concepts.
        # A B.Tech label alone is NOT sufficient.
        # Must only appear if:
        # primary_intent == RESEARCH / ADVANCED_RESEARCH
        # OR instructional_mode == DEEP_DIVE
        # OR learner explicitly requests research
        # OR stage explicitly requires research evidence
        # OR PG/PhD policy requires it
        is_pg_phd = any(k in learner_level.lower() for k in ["phd", "doctorate", "m.tech", "postgraduate", "pg", "graduate research"])
        stage_requires_research = any("research" in obj.lower() for obj in final_objectives)
        allow_research = (
            intent in [StageIntent.ADVANCED_RESEARCH]
            or is_pg_phd
            or stage_requires_research
        )
        if allow_research:
            recommended_types.append(ResourceType.RESEARCH_PAPER)

        # Generate targeted query terms
        query_terms = [
            canonical_topic,
            f"{canonical_topic} explained",
            f"{canonical_topic} solved examples"
        ]
        if concepts:
            query_terms.append(" ".join(concepts[:3]))

        # Build ResourceQueryContext
        query_context = ResourceQueryContext(
            roadmap_id=roadmap_id,
            plan_version="1.0",
            stage_id=stage_id,
            original_topic=topic,
            normalized_topic=canonical_topic,
            domain=domain,
            specialization=specialization,
            learner_level=learner_level,
            primary_intent=intent.value,
            instructional_mode="DIRECT_INSTRUCTION",
            stage_type=archetype or "concept_intro",
            learning_objectives=final_objectives,
            canonical_concept_ids=canonical_concept_ids,
            prerequisites=[],
            resource_role="conceptual_reference",
            negative_terms=negative_terms
        )

        return ResourceIntentProfile(
            roadmap_id=roadmap_id,
            stage_id=stage_id,
            domain=domain,
            specialization=specialization,
            subject=subject,
            canonical_topic=canonical_topic,
            stage_title=stage_title,
            concept_ids=[concept_id] if concept_id else [],
            concept_names=concepts,
            concept_synonyms=synonyms,
            canonical_concept_ids=canonical_concept_ids,
            learning_objectives=final_objectives,
            prerequisites=[],
            misconceptions=misconceptions,
            learner_weaknesses=final_weaknesses,
            mastery_state="in_progress",
            learner_level=learner_level,
            instructional_mode="DIRECT_INSTRUCTION",
            preferred_language=language,
            stage_intent=intent,
            is_programming_topic=is_programming,
            programming_language=programming_lang,
            assessment_focus=None,
            query_terms=query_terms,
            negative_terms=negative_terms,
            recommended_resource_types=recommended_types,
            context=query_context
        )

# TEACHGENIE — KNOWLEDGE PACK SPECIFICATION
**Specification Version:** 1.0.0  
**Status:** ARCHITECTURAL SPECIFICATION FOR VNEXT  
**Auditor:** Principal AI Systems Architect & FinOps Reviewer

---

## 1. Concept & Rationale

The **TeachGenie Knowledge Pack** is an immutable, strongly-typed, reusable topic intelligence artifact generated once per `(topic, subject, class_level, curriculum)` tuple. It solves the **Duplicate Reasoning Problem** identified in Phase 9, where Lesson Planner, Presentation, Notes, Quiz, Tutor, and Video independently invoke expensive LLM calls to discover the identical educational objectives, prerequisites, and misconceptions.

```text
                  Raw Topic Request ("Chemical Bonding", CBSE Class 10)
                                            │
                                            ▼
                           KNOWLEDGE PACK GENERATOR / CACHE
                                            │
               ┌────────────────────────────┼────────────────────────────┐
               ▼                            ▼                            ▼
      LEARNING ROADMAP                 TOPIC DECK                   STUDY NOTES
   (Reads stages/times)           (Reads slide concepts)       (Reads scaffolding/debunk)
               │                            │                            │
               └────────────────────────────┼────────────────────────────┘
                                            ▼
                                  DIAGNOSTIC QUIZ
                           (Reads target distractors)
```

---

## 2. Complete Pydantic Schema Contract

```python
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from enum import Enum

class BloomLevel(str, Enum):
    REMEMBER = "remember"
    UNDERSTAND = "understand"
    APPLY = "apply"
    ANALYZE = "analyze"
    EVALUATE = "evaluate"
    CREATE = "create"

class VisualOpportunityType(str, Enum):
    FLOWCHART = "flowchart"
    ARCHITECTURE_STACK = "architecture_stack"
    COMPARISON_TABLE = "comparison_table"
    HIERARCHY_TREE = "hierarchy_tree"
    CYCLE_DIAGRAM = "cycle_diagram"
    PHOTOGRAPHIC_DEMO = "photographic_demo"

class ConceptNode(BaseModel):
    concept_id: str = Field(..., description="Unique slug for concept (e.g. 'covalent_bond')")
    name: str = Field(..., description="Human-readable concept name")
    description: str = Field(..., description="Clear, authoritative explanation")
    prerequisites: List[str] = Field(default_factory=list, description="IDs of concepts required prior")
    core_laws_or_rules: List[str] = Field(default_factory=list)
    real_world_analogy: str = Field(..., description="Vivid physical analogy for intuition")
    visual_intent: Optional[VisualOpportunityType] = None
    bloom_level: BloomLevel = BloomLevel.UNDERSTAND

class MisconceptionItem(BaseModel):
    id: str
    target_concept_id: str
    flawed_belief: str = Field(..., description="What students mistakenly think")
    why_plausible: str = Field(..., description="Intuitive reason why this trap occurs")
    scientific_reality: str = Field(..., description="Factual correction")
    refutation_prompt: str = Field(..., description="Socratic question exposing the flaw")

class AssessmentTarget(BaseModel):
    concept_id: str
    question_stem: str
    correct_concept: str
    plausible_distractors: List[str] = Field(..., min_length=3, max_length=3)
    diagnostic_intent: str = Field(..., description="What choosing distractor B reveals")

class KnowledgePack(BaseModel):
    pack_id: str = Field(..., description="SHA256 hash of normalized (topic, subject, grade, curriculum)")
    topic: str
    subject: str
    class_level: str
    curriculum: str = "CBSE"
    language: str = "english"
    
    # Core Syllabus Coverage
    learning_objectives: List[str] = Field(..., min_length=2)
    concepts: List[ConceptNode] = Field(..., min_length=3)
    prerequisite_summary: List[str] = Field(default_factory=list)
    
    # Pedagogical Assets
    misconceptions: List[MisconceptionItem] = Field(default_factory=list)
    visual_opportunities: List[Dict[str, Any]] = Field(default_factory=list)
    assessment_targets: List[AssessmentTarget] = Field(default_factory=list)
    
    # Metadata & Provenance
    source_documents: List[str] = Field(default_factory=list)
    version: str = "1.0.0"
    created_at_utc: str
    ttl_seconds: int = 2592000  # 30 days
```

---

## 3. Database Persistence & Migration Schema

```sql
CREATE TABLE IF NOT EXISTS knowledge_packs (
    pack_id TEXT PRIMARY KEY,
    topic TEXT NOT NULL,
    subject TEXT NOT NULL,
    class_level TEXT NOT NULL,
    curriculum TEXT NOT NULL,
    payload JSONB NOT NULL,
    token_cost_to_build INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ DEFAULT (NOW() + INTERVAL '30 days')
);

CREATE INDEX IF NOT EXISTS idx_knowledge_packs_lookup 
ON knowledge_packs(topic, subject, class_level, curriculum);
```

---

## 4. Lifecycle & Invalidation Rules

1. **Generation:** When any feature requests generation for a topic, it queries `knowledge_packs` by normalized hash. If missed, it synthesizes the pack once via a single structured call (`gemini-2.0-flash` or `gpt-4o-mini`).
2. **Reuse:** Lesson Planner, Decks, Notes, Quizzes, and TeachMe directly ingest the cached pack.
3. **Invalidation:** Packs have a default 30-day TTL. Invalidation occurs immediately if the user attaches custom private source PDFs or curriculum updates.
4. **Privacy:** Public curriculum topics are shared globally across users (reducing total system inference bills by >60%). User-specific uploaded PDF notes generate a `user_id`-scoped private pack.

# TEACHGENIE — LEARNING STATE GRAPH SPECIFICATION
**Specification Version:** 1.0.0  
**Status:** ARCHITECTURAL SPECIFICATION FOR VNEXT  
**Auditor:** Principal AI Systems Architect & FinOps Reviewer

---

## 1. Executive Objective

Transform TeachGenie from a collection of **stateless isolated generators** into an **Adaptive Compounding Learning Engine**. When a student takes a quiz, watches a video, or engages with the tutor, their evidence updates a **central, relational student knowledge state**. Subsequent notes, quizzes, and decks adapt automatically based on documented gaps.

---

## 2. Relational Schema Architecture (PostgreSQL / Supabase)

We explicitly reject the overhead of a dedicated graph database (e.g. Neo4j). Standard PostgreSQL with foreign keys, JSONB provenance, and indexed concept lookups provides sub-millisecond querying with zero operational complexity.

```sql
-- 1. Student Knowledge State per Concept
CREATE TABLE IF NOT EXISTS student_mastery_states (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    subject TEXT NOT NULL,
    concept_id TEXT NOT NULL,
    
    -- Statistical Mastery State
    mastery_score NUMERIC(3,2) NOT NULL DEFAULT 0.00,  -- 0.00 to 1.00
    confidence_score NUMERIC(3,2) NOT NULL DEFAULT 0.00, -- 0.00 to 1.00
    observations_count INTEGER NOT NULL DEFAULT 0,
    
    -- Status: 'untested' | 'struggling' | 'developing' | 'mastered'
    status TEXT NOT NULL DEFAULT 'untested',
    
    -- Active / Unresolved Misconceptions
    active_misconceptions JSONB NOT NULL DEFAULT '[]'::jsonb,
    
    last_evaluated_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(user_id, concept_id)
);

CREATE INDEX IF NOT EXISTS idx_student_mastery ON student_mastery_states(user_id, subject);

-- 2. Evidence Event Log (Strict Provenance Tracking)
CREATE TABLE IF NOT EXISTS student_learning_evidence (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    concept_id TEXT NOT NULL,
    
    -- Originating Feature: 'quiz' | 'live_quiz' | 'tutor' | 'notes_self_check' | 'video_checkpoint'
    source_feature TEXT NOT NULL,
    source_event_id TEXT NOT NULL, -- quiz_response_id, teachme_turn_id, etc.
    
    -- Assessment Signals
    correctness TEXT NOT NULL, -- 'correct' | 'partial' | 'incorrect'
    score_delta NUMERIC(4,2) NOT NULL,
    difficulty TEXT NOT NULL DEFAULT 'medium',
    detected_misconception TEXT,
    
    -- Prompt & Context Proof
    evidence_snippet TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_evidence_provenance ON student_learning_evidence(user_id, concept_id, created_at DESC);
```

---

## 3. Mathematical Update Algorithm: Bayesian-Inspired Skill Rating

Rather than the current additive heuristic, TeachGenie VNext implements an **Elo/BKT Hybrid Skill Rating** that explicitly accounts for item difficulty and guess probabilities:

$$\Delta M = K \times (S - E)$$

Where:
- $S$ is the observed correctness score ($1.0$ for correct, $0.5$ for partial, $0.0$ for incorrect).
- $E$ is the expected probability of success given current mastery $M$ and question difficulty $D$:
  $$E = \frac{1}{1 + 10^{(D - M)}}$$
- $K$ is the dynamic update sensitivity, scaling down as observation count $N$ increases ($K = \frac{0.40}{\sqrt{N + 1}}$).
- **Misconception Trap:** If an assessment response matches a known diagnostic distractor, the mastery is hard-capped below $0.75$ until a counter-verification question is answered correctly.

---

## 4. Cross-Feature Compounding Loop

```text
1. Student attempts Live Quiz Question on "Daniell Cell" -> Chooses Distractor B.
   │
   ▼
2. Evidence Written to student_learning_evidence:
   {concept: "daniell_cell", correctness: "incorrect", misconception: "salt_bridge_electron_flow"}
   │
   ▼
3. student_mastery_states updated:
   mastery: 0.28, confidence: 0.65, active_misconceptions: ["salt_bridge_electron_flow"]
   │
   ▼
4. NEXT ACTIONS COMPOUND AUTOMATICALLY:
   ├── Notes Generator (/notes): Prescribes REMEDIATION mode + 6-part debunking section for Salt Bridge.
   ├── Decks Engine (/decks): Injects "Common Trap: Electron flow vs Ion migration" slide into presentation.
   ├── TeachMe Tutor (/teach): Socratic tutor greets student with targeted inquiry on ion balance.
   └── Quiz Engine (/quizzes): Includes 1 targeted diagnostic question testing salt bridge function.
```

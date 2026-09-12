# 2026 EDTECH & PRESENTATION COMPETITIVE AUDIT

## 1. Official Capability Audit Matrix

Every competitor was evaluated against official product releases and feature specifications as of September 2026.

| Platform | Core Category | Persistent Learner State | Misconception Ontology | Cross-Artifact State Sharing | Dynamic Mid-Lesson Replanning | Pedagogical Slide Grammar | Source Grounding Precision |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Gamma** | Presentation AI | ❌ Absent | ❌ Absent | ❌ Absent | ❌ Absent | 🟡 Partial (Web card UI) | ❌ Absent (Uncited) |
| **Beautiful.ai** | Presentation AI | ❌ Absent | ❌ Absent | ❌ Absent | ❌ Absent | 🟡 Partial (Smart templates)| ❌ Absent |
| **Canva Magic** | Design Suite | ❌ Absent | ❌ Absent | ❌ Absent | ❌ Absent | ❌ Absent (Generic text box)| ❌ Absent |
| **MagicSchool AI** | Teacher Copilot | ❌ Absent (Stateless) | ❌ Absent | ❌ Absent (Siloed tools)| ❌ Absent (Static docs) | ❌ Absent (Plain text)| 🟡 Partial (URL paste) |
| **SchoolAI** | Student Space / Tutor | 🟡 Partial (Session notes)| 🟡 Partial (Flagged keywords)| ❌ Absent (Siloed in space)| ❌ Absent | ❌ Absent (No PPT engine) | 🟡 Partial (Doc upload) |
| **Curipod** | Interactive Polls | 🟡 Partial (Per-session poll)| ❌ Absent (Word clouds) | ❌ Absent | ❌ Absent (Static slides)| 🟡 Partial (Poll slides) | ❌ Absent |
| **NotebookLM** | Research Assistant | ❌ Absent | ❌ Absent | ❌ Absent | ❌ Absent | ❌ Absent (Audio/Notes only)| ✅ Strong (Source cited) |
| **Khanmigo** | Socratic Chatbot | 🟡 Partial (Khan course state)| 🟡 Partial (Khan exercise hints)| ❌ Absent (Siloed to Khan exercises)| ❌ Absent | ❌ Absent | 🟡 Partial (Khan content) |
| **ChatGPT / Claude Edu**| General LLM | 🟡 Partial (Custom GPT / Memory)| ❌ Absent (General weights)| ❌ Absent | ❌ Absent | ❌ Absent (Raw text dump)| 🟡 Partial (Web/File RAG) |
| **TeachGenie vNext** | Unified Intelligence | **✅ Verified Target (Postgres Graph)**| **✅ Verified (KnowledgePack)**| **✅ Verified Target (Single Learning State)**| **✅ Verified Target (Live Quiz Loop)**| **✅ Verified (Archetype Compiler)**| **✅ Verified (Page-level anchors)**|

---

## 2. Gate 22: The Cross-Artifact Closed-Loop Verification

### Question: Does any existing market product connect cross-feature state?
Can a competitor currently execute this workflow?
```text
Quiz mistake on Concept A
      ↓
Concept evidence recorded
      ↓
Mastery update in shared graph
      ↓
Next Tutor turn probes prerequisite of Concept A
      ↓
Notes generator inserts targeted repair block for Concept A
      ↓
Next presentation emphasizes Concept A misconception
      ↓
Lesson planner compresses pacing and inserts a 5-minute reteach
      ↓
YouTube/Video recommender surfaces 2-minute timestamped clip for Concept A
```

### Competitor Findings:
1. **SchoolAI**: Excellent student "Spaces" with real-time teacher dashboards, but **it has no presentation generator, no video generator, and no unified syllabus lesson planner**. Insights remain locked inside the chat session transcript.
2. **MagicSchool**: Offers 60+ individual AI tools (Lesson Plan Generator, Rubric Generator, Quiz Generator), but **they are completely isolated prompt wrappers**. Generating a quiz does not inform the lesson planner, nor does it track student answers.
3. **Khanmigo**: Tracks student progress strictly within Khan Academy's pre-authored exercise problem sets. It cannot generate customized PowerPoint presentations, downloadable teacher slides, or dynamic lesson plans for local school curricula (CBSE/ICSE/State Boards).
4. **Gamma / Canva**: Pure presentation tools with zero concept of a "student", "mastery", or "misconception".

### Definitive Conclusion:
**No existing product in the 2026 market connects assessment evidence to presentation generation, study notes repair, and dynamic lesson planning.**
The industry remains fragmented into **Content Generators (Gamma, MagicSchool)** and **Activity Monitors (SchoolAI, Kahoot)**.
TeachGenie's cross-artifact closed loop is a **genuine, defensible architectural differentiator**.

# TEACHGENIE — 2026 COMPETITIVE MARKET BENCHMARK
**Research Date:** September 12, 2026  
**Auditor:** Principal AI Systems Architect & Competitive Intelligence Researcher  
**Evidence Standard:** Based strictly on documented product capabilities and official release notes.

---

## 1. Competitive Capability Matrix

Legend:
- ✅ **Strong / Native Capability**
- 🟡 **Partial / Surface-Level Implementation**
- ❌ **Absent / Not Supported**
- ❓ **Unverified**

| Capability Dimension | TeachGenie (Current) | Gamma App | Canva Magic Studio | Beautiful.ai | MS PowerPoint Copilot | MagicSchool AI | SchoolAI | Curipod | Google NotebookLM | Khanmigo |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Editable PPTX Export** | ✅ (python-pptx) | ✅ (Export) | ✅ (Export) | ✅ (Export) | ✅ (Native) | ❌ (Text only) | ❌ (Text only) | 🟡 (Export) | ❌ (Text/Audio) | ❌ |
| **Topic $\rightarrow$ Presentation** | ✅ | ✅ | ✅ | ✅ | 🟡 (Requires Word doc) | 🟡 (Outline only) | ❌ | ✅ (Deck gen) | ❌ | ❌ |
| **Instructional Narrative Architecture** | 🟡 (Planner + Reviewer) | 🟡 (Aesthetic cards) | ❌ (Generic templates) | 🟡 (Smart slides) | ❌ (Corporate bullets) | 🟡 (Lesson outline) | ❌ | ✅ (Interactive) | ❌ | ❌ |
| **Automated Misconception Debunking** | ✅ (6-stage debunk) | ❌ | ❌ | ❌ | ❌ | 🟡 (Misconception tool) | 🟡 (Tutor space) | ❌ | ❌ | 🟡 (Tutor) |
| **Deterministic Page-Budgeted Notes** | ✅ (5-8 A4 pages) | ❌ | ❌ | ❌ | ❌ | 🟡 (Unbounded text) | ❌ | ❌ | ✅ (Source notebook) | ❌ |
| **Source Document Grounding (RAG)** | ✅ (pgvector) | 🟡 (Import URL) | ❌ | ❌ | ✅ (SharePoint RAG) | 🟡 (Context field) | 🟡 (Space upload) | ❌ | ✅ (Grounding leader) | ❌ |
| **Multiplayer Live Classroom Quizzing** | ✅ (PIN join + Realtime) | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ (Core feature) | ❌ | ❌ |
| **Live Remedial Interventions** | ✅ (SVG + Explain) | ❌ | ❌ | ❌ | ❌ | ❌ | 🟡 (Teacher flag) | 🟡 (AI feedback) | ❌ | ❌ |
| **Stateful Socratic Tutor with Checkpoints** | ✅ (TeachMe) | ❌ | ❌ | ❌ | ❌ | 🟡 (Raina Chatbot) | ✅ (Spaces) | ❌ | ❌ | ✅ (Socratic leader) |
| **Automated Macro-Curriculum Planning** | ✅ (Roadmaps) | ❌ | ❌ | ❌ | ❌ | ✅ (Unit planner) | ❌ | ❌ | ❌ | ❌ |
| **Video Generation with Narration** | ✅ (edge-tts + FFmpeg) | ❌ | 🟡 (Video clips) | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ (Audio Podcast) | ❌ |
| **Cross-Feature Compounding State** | ❌ (Currently siloed) | ❌ | ❌ | ❌ | 🟡 (Microsoft Graph) | ❌ | 🟡 (Student history) | ❌ | ❌ | 🟡 (Mastery map) |
| **Deterministic Quality Certification** | ✅ (Zero-LLM QA Gate) | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |

---

## 2. In-Depth Competitor Analysis: What They Do Better vs. TeachGenie

### A. Presentation Competitors (Gamma, Beautiful.ai, Canva)
- **Gamma.app:**
  - *Where Gamma wins:* Superior dynamic web-native card UX, fluid responsive reflow, rich nested media embeds, and interactive widgets.
  - *Where Gamma fails education:* Slides are generic marketing/business cards; zero syllabus alignment; no pedagogical sequencing (no concept checks, no formal definitions vs intuition scaffolding, no misconception debunking).
- **Beautiful.ai:**
  - *Where Beautiful.ai wins:* True rule-based layout constraint engine ("Smart Slides"). Text and charts reposition themselves dynamically without clipping or overflow.
  - *Where Beautiful.ai fails education:* Pure corporate sales focus. Zero learning science.
- **Canva Magic Studio:**
  - *Where Canva wins:* Millions of licensed design assets, beautiful typography, multi-modal brand kits.
  - *Where Canva fails education:* Generates superficial bulleted slides with generic stock photos. No depth.

### B. Education AI Competitors (MagicSchool, SchoolAI, Curipod, Khanmigo, NotebookLM)
- **MagicSchool AI:**
  - *Where MagicSchool wins:* 60+ pre-built prompt templates for teachers (rubrics, IEPs, emails, lesson starters); massive K-12 teacher adoption.
  - *Where MagicSchool fails:* It is fundamentally an **unbundled prompt wrapper over Claude/GPT-4**. It does not generate compiled artifacts (no native PPTX, no print-formatted multi-page PDFs), has zero live classroom interactivity, and does not track student learning state over time.
- **SchoolAI:**
  - *Where SchoolAI wins:* Live student spaces where teachers monitor 30 students simultaneously talking to customized AI sidekicks.
  - *Where SchoolAI fails:* Text-heavy; no integrated presentation compiler, no structured notes engine, no automated video lesson generation.
- **Curipod:**
  - *Where Curipod wins:* Interactive live slide decks with instant student drawing, word clouds, and AI feedback during presentations.
  - *Where Curipod fails:* Shallow content depth; decks are short (5-7 slides); no deep notes or long-form lesson roadmaps.
- **Google NotebookLM:**
  - *Where NotebookLM wins:* Gold standard for multi-document factual grounding, citation tracing, and viral Audio Overview (two-host audio podcast discussion).
  - *Where NotebookLM fails:* Purely analytical study aid for adults; cannot generate classroom presentations, quizzes, or structured curriculum lesson plans.

---

## 3. The Unoccupied Market White Space for TeachGenie

Current market products are fractured into two distinct, unintegrated categories:
1. **Design-first corporate presentation tools** (Gamma, Canva, Beautiful.ai) that know **nothing about how students learn**.
2. **Prompt-wrapper teacher tools** (MagicSchool, Eduaide) that produce **unformatted wall-of-text prompts** without compiling production-ready artifacts.

> **TEACHGENIE'S DEFICIT & OPPORTUNITY:**
> TeachGenie can become the **only integrated educational compiler** that takes learner context and outputs **production-grade educational artifacts** (native `.pptx`, certified A4 `.pdf` notes, diagnostic quizzes, and synchronized `.mp4` video) while utilizing shared student mastery evidence to make every subsequent artifact smarter and cheaper.

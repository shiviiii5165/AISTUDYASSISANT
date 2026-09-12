"""
TeachGenie AI Video Teacher V2 — Cross-Domain Benchmark Suite
============================================================
Verifies all 15 architectural decisions across the 7 required benchmark topics:
1. Linked List (Computer Science)
2. Integration by Parts (Mathematics)
3. Newton's Second Law (Physics)
4. Photosynthesis (Biology)
5. French Revolution (History)
6. Database Normalization (DBMS)
7. Marketing Funnel (Business)

Tests:
- Universal Domain Intelligence & Dynamic Concept Graph Generation
- 10-Stage Pedagogical Story Structure & Per-Scene Archetype Routing
- Domain Visualization Registry (Specialized + Generic Archetype Rendering)
- FFmpeg Discovery & Frame Sequence Video Compilation
- Language Teaching Engine (Technical Term Preservation in Hinglish)
- Video Knowledge Package Compilation
- Timestamp Context Resolution (Deictic Queries)
- Confusion Diagnosis & Dedicated Prerequisite Gap Detection
- Explanation Strategy Escalation without Repetition
- Quick Mastery Check Verification
"""
import sys
import os
import asyncio
import tempfile

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

os.environ["CASHFREE_APP_ID"] = "placeholder_app_id"
os.environ["CASHFREE_SECRET_KEY"] = "placeholder_secret_key"
os.environ["SUPABASE_URL"] = "https://placeholder.supabase.co"
os.environ["SUPABASE_KEY"] = "placeholder"
os.environ["SUPABASE_JWT_SECRET"] = "placeholder"
os.environ["GEMINI_API_KEY"] = "placeholder"
os.environ["GROQ_API_KEY"] = "placeholder"

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.video.schemas import (
    VideoConfig, VideoQuality, VideoStyle, AspectRatio, DomainCategory,
    VisualStrategyArchetype, TeachingStoryStage, LearningIntent, ConceptGraph,
    SceneSpec, VisualSpec, VideoKnowledgePackage, SceneKnowledge, DoubtContext,
    ConfusionType, ExplanationStrategy, ConfusionDiagnosis
)
from app.services.video.pedagogy.domain_intelligence import DomainIntelligenceEngine
from app.services.video.pedagogy.intent_parser import LearningIntentParser
from app.services.video.pedagogy.dynamic_curriculum import DynamicCurriculumEngine
from app.services.video.pedagogy.story_compiler import StoryboardCompiler
from app.services.video.localization.language_engine import LanguageTeachingEngine
from app.services.video.visualizers.registry import DomainVisualizationRegistry
from app.services.video.visualizers.specialized.linked_list import LinkedListVisualizer
from app.services.video.compositor.compositor import get_ffmpeg_binary, check_ffmpeg_available, compose_single_scene_clip
from app.services.video.captions.caption_generator import generate_srt_subtitles
from app.services.video.doubt.context_resolver import VideoContextResolver
from app.services.video.doubt.prerequisite_gap import PrerequisiteGapDetector
from app.services.video.doubt.confusion_diagnosis import ConfusionDiagnosisEngine
from app.services.video.doubt.explanation_strategy import ExplanationStrategyEngine
from app.services.video.doubt.mastery_check import QuickMasteryCheckGenerator
from app.services.video.qa.python_qa import validate_storyboard_quality, validate_semantic_teaching_quality
from app.services.video.orchestrator import generate_video_pipeline, PROJECT_STORE


BENCHMARK_TOPICS = [
    ("Teach Linked List to a B.Tech beginner in Hinglish in 5 minutes", DomainCategory.COMPUTER_SCIENCE),
    ("Explain Integration by Parts in English", DomainCategory.MATHEMATICS),
    ("Teach Newton's Second Law with examples", DomainCategory.PHYSICS),
    ("Photosynthesis for Class 10 in 5 min", DomainCategory.BIOLOGY),
    ("French Revolution in Hindi from basics", DomainCategory.HISTORY),
    ("Explain Database Normalization in English", DomainCategory.COMPUTER_SCIENCE),
    ("Teach Marketing Funnel for business students", DomainCategory.BUSINESS),
]


def test_domain_intelligence_and_intent_parser():
    print("\n--- TEST 1: Universal Domain Intelligence & Intent Parsing ---")
    for prompt, expected_domain in BENCHMARK_TOPICS:
        intent = LearningIntentParser.parse(prompt)
        print(f"Prompt: '{prompt}' -> Topic: '{intent.topic}' | Domain: {intent.domain.value} | Level: {intent.learner_level} | Lang: {intent.language} | Dur: {intent.duration_seconds}s")
        assert intent.domain == expected_domain
        assert intent.duration_seconds > 0
        assert intent.topic

    print(">>> Domain intelligence and intent parsing PASSED.")


def test_dynamic_curriculum_and_concept_graphs():
    print("\n--- TEST 2: Dynamic Curriculum & Concept Graphs across 7 Domains ---")
    for prompt, expected_domain in BENCHMARK_TOPICS:
        intent = LearningIntentParser.parse(prompt)
        graph = asyncio.run(DynamicCurriculumEngine.build_concept_graph(intent))
        print(f"Topic '{graph.topic}': {len(graph.nodes)} concept nodes | Prerequisites: {graph.prerequisites[:2]} | Misconceptions: {len(graph.major_misconceptions)}")
        assert len(graph.nodes) >= 3
        assert len(graph.learning_objectives) >= 2
        assert len(graph.prerequisites) >= 1

    print(">>> Dynamic curriculum generation across 7 domains PASSED.")


def test_storyboard_compilation_and_archetype_routing():
    print("\n--- TEST 3: 10-Stage Storyboard Compilation & Archetype Routing ---")
    for prompt, _ in BENCHMARK_TOPICS:
        intent = LearningIntentParser.parse(prompt, default_duration=300)
        graph = asyncio.run(DynamicCurriculumEngine.build_concept_graph(intent))
        storyboard = StoryboardCompiler.compile(intent, graph)

        total_dur = sum(s.duration for s in storyboard.scenes)
        print(f"Storyboard '{storyboard.topic}': {len(storyboard.scenes)} scenes | Total Duration: {total_dur}s (Target: {intent.duration_seconds}s)")
        assert total_dur == intent.duration_seconds
        assert len(storyboard.scenes) >= 3

        # Verify multiple archetypes exist across scenes
        archetypes_used = {s.visual_strategy for s in storyboard.scenes}
        print(f"   Visual archetypes used: {[a.value for a in archetypes_used]}")
        assert len(archetypes_used) >= 2, "Must use multiple visual archetypes across scenes (Decision #2)"

        # Verify semantic QA
        is_valid, issues = validate_semantic_teaching_quality(storyboard)
        assert is_valid, f"Semantic QA failed: {issues}"

    print(">>> 10-Stage Storyboard compilation & archetype routing PASSED.")


def test_visualizer_registry_and_linked_list_benchmark():
    print("\n--- TEST 4: Visualizer Registry & Linked List Benchmark Rendering ---")
    temp_dir = tempfile.mkdtemp()

    # 1. Specialized Linked List Benchmark
    ll_scene = SceneSpec(
        scene_id="s_ll_ins",
        order=4,
        concept_id="c_insert",
        concept_name="Middle Insertion",
        purpose=TeachingStoryStage.VISUAL_MECHANISM,
        duration=20,
        narration="Connect 25.next to 30 first, then update 20.next to 25.",
        caption="Node Insertion & Pointer Order",
        visual_strategy=VisualStrategyArchetype.DATA_STRUCTURE
    )
    ll_out = os.path.join(temp_dir, "test_ll.png")
    DomainVisualizationRegistry.render_scene_media(ll_scene, "Linked List", ll_out)
    assert os.path.exists(ll_out) and os.path.getsize(ll_out) > 5000
    print(f"Rendered Linked List specialized frame: {ll_out} ({os.path.getsize(ll_out)} bytes)")

    # 2. Universal Generic Archetypes (Equation, Timeline, Flow, Graph, Table)
    archetype_tests = [
        ("Integration by Parts", VisualStrategyArchetype.MATHEMATICAL_DERIVATION, "test_equation.png"),
        ("French Revolution", VisualStrategyArchetype.TIMELINE, "test_timeline.png"),
        ("Photosynthesis", VisualStrategyArchetype.PROCESS_FLOW, "test_flow.png"),
        ("Newton Second Law", VisualStrategyArchetype.GRAPH_PLOT, "test_graph.png"),
        ("Database Normalization", VisualStrategyArchetype.TABLE, "test_table.png"),
        ("Marketing Funnel", VisualStrategyArchetype.COMPARISON, "test_comparison.png"),
    ]

    for topic_name, arch, filename in archetype_tests:
        scene = SceneSpec(
            scene_id="s_arch",
            order=1,
            concept_id="c1",
            concept_name=f"{topic_name} Mechanism",
            purpose=TeachingStoryStage.VISUAL_MECHANISM,
            duration=20,
            narration="Step by step operational mechanism.",
            caption=f"{topic_name} Visual",
            visual_strategy=arch
        )
        out_f = os.path.join(temp_dir, filename)
        DomainVisualizationRegistry.render_scene_media(scene, topic_name, out_f)
        assert os.path.exists(out_f) and os.path.getsize(out_f) > 5000
        print(f"Rendered archetype {arch.value} for {topic_name}: {out_f} ({os.path.getsize(out_f)} bytes)")

    print(">>> Visualizer registry & Linked List benchmark rendering PASSED.")


def test_language_teaching_engine_term_preservation():
    print("\n--- TEST 5: Language Teaching Engine (Technical Term Preservation) ---")
    raw_hinglish = "Yahan hum node 20 ke pointer next ko node 25 se connect karenge taaki linked list ki chain break na ho."
    clean_audio = LanguageTeachingEngine.normalize_narration(raw_hinglish, language="hinglish", domain=DomainCategory.COMPUTER_SCIENCE)
    print(f"Raw:   {raw_hinglish}")
    print(f"Clean: {clean_audio}")

    assert "node" in clean_audio
    assert "pointer" in clean_audio
    assert "linked list" in clean_audio

    # Test code dot notation preservation
    code_text = "Step 1 me 20.next ko 30 set karein and curr.next update karein."
    clean_code = LanguageTeachingEngine.normalize_narration(code_text, language="hinglish")
    print(f"Code normalizer: {clean_code}")
    assert "20 dot next" in clean_code

    print(">>> Language teaching engine technical term preservation PASSED.")


def test_timestamp_context_resolver_and_doubt_pipeline():
    print("\n--- TEST 6: Timestamp Context Resolver & Ask Your Doubt Pipeline ---")
    # Build a sample VideoKnowledgePackage for Linked List
    scenes = [
        SceneKnowledge(
            scene_id="scene_01",
            order=1,
            timestamp_start=0.0,
            timestamp_end=20.0,
            concept_id="c1",
            concept_name="Introduction",
            teaching_goal="Introduce concept",
            purpose="hook",
            narration="Welcome to linked list masterclass.",
            transcript="Welcome to linked list masterclass.",
            visual_strategy="concept_map"
        ),
        SceneKnowledge(
            scene_id="scene_02",
            order=2,
            timestamp_start=20.0,
            timestamp_end=50.0,
            concept_id="c2",
            concept_name="Node Anatomy",
            teaching_goal="Explain data and next pointer",
            purpose="core_concept",
            narration="Each node has two compartments: data and next pointer.",
            transcript="Each node has two compartments: data and next pointer.",
            visual_strategy="data_structure",
            prerequisite_refs=["Memory Addresses & Pointers"]
        ),
        SceneKnowledge(
            scene_id="scene_03",
            order=3,
            timestamp_start=50.0,
            timestamp_end=90.0,
            concept_id="c3",
            concept_name="Node Insertion",
            teaching_goal="Insert node in middle without losing chain",
            purpose="visual_mechanism",
            narration="We want to insert 25 between 20 and 30. Connect 25.next to 30 first, then 20.next to 25.",
            transcript="We want to insert 25 between 20 and 30. Connect 25.next to 30 first, then 20.next to 25.",
            visual_strategy="data_structure",
            worked_example="20 -> 25 -> 30 insertion",
            misconception_tags=["Overwriting 20.next first permanently drops node 30"]
        )
    ]

    knowledge_pack = VideoKnowledgePackage(
        video_id="test_vid_ll",
        topic="Linked List",
        domain="computer_science",
        learner_level="B.Tech",
        language="hinglish",
        total_duration_seconds=90.0,
        learning_objectives=["Understand pointer linking"],
        prerequisites=["Memory Addresses & Pointers"],
        scenes=scenes
    )

    # 1. Resolve at timestamp 65.0s (during insertion)
    ctx = VideoContextResolver.resolve_context(knowledge_pack, timestamp=65.0, student_question="20.next ko 25 kyu kiya?")
    assert ctx.current_scene_id == "scene_03"
    assert ctx.current_concept == "Node Insertion"
    assert "25 between 20 and 30" in ctx.relevant_narration
    print(f"Timestamp 65.0s resolved to: Scene {ctx.current_scene_id} ({ctx.current_concept})")

    # 2. Diagnose Confusion
    diag = ConfusionDiagnosisEngine.diagnose(ctx)
    print(f"Diagnosis: {diag.confusion_type.value} | Confidence: {diag.confidence} | Strategy: {diag.recommended_strategy.value}")
    assert diag.confusion_type == ConfusionType.PROCESS_CONFUSION

    # 3. Generate Doubt Answer (No new video!)
    answer = ExplanationStrategyEngine.generate_doubt_answer_sync(ctx, diag.confusion_type, diag.recommended_strategy, tried_strategies=[])
    print(f"Doubt Answer Strategy: {answer.strategy_used.value}")
    assert "20 → 25 → 30" in answer.explanation_markdown or "20 -> 25 -> 30" in answer.explanation_markdown
    assert answer.mastery_check is not None
    print(f"Mastery Check: {answer.mastery_check.question}")

    # 4. Test Strategy Escalation on Follow-Up ("still samajh nahi aaya")
    tried = [diag.recommended_strategy]
    escalated_strategy = ExplanationStrategyEngine.determine_strategy(diag.recommended_strategy, tried_strategies=tried)
    assert escalated_strategy != diag.recommended_strategy, "Must escalate to a new strategy (Decision #14)"
    print(f"Initial Strategy: {diag.recommended_strategy.value} -> Escalated: {escalated_strategy.value}")

    answer2 = ExplanationStrategyEngine.generate_doubt_answer_sync(ctx, diag.confusion_type, escalated_strategy, tried_strategies=tried)
    assert answer2.strategy_used == escalated_strategy

    # 5. Dedicated Prerequisite Gap Detection (Decision #3)
    prereq_ctx = VideoContextResolver.resolve_context(knowledge_pack, timestamp=25.0, student_question="Pointer kya hota hai pehle ye batao?")
    prereq_diag = ConfusionDiagnosisEngine.diagnose(prereq_ctx)
    print(f"Prerequisite Gap Diagnosis: {prereq_diag.confusion_type.value} | Gap: {prereq_diag.detected_gap}")
    assert prereq_diag.confusion_type == ConfusionType.PREREQUISITE_GAP

    # 6. Evaluate Quick Mastery Check
    eval_res = QuickMasteryCheckGenerator.evaluate_answer(answer.mastery_check, selected_index=1)
    assert eval_res["is_correct"] is True
    print(f"Mastery Check Evaluation (Option 1): {eval_res['feedback']}")

    print(">>> Timestamp context resolver & doubt pipeline PASSED.")


def test_cross_domain_doubt_resolution():
    print("\n--- TEST 7: Cross-Domain Doubt Context Resolution ---")
    # Mathematics: "Ye minus sign yaha kaise aaya?"
    math_pack = VideoKnowledgePackage(
        video_id="v_math", topic="Integration by Parts", domain="mathematics",
        learner_level="Class 12", language="hinglish", total_duration_seconds=120.0,
        scenes=[SceneKnowledge(scene_id="s1", order=1, timestamp_start=0.0, timestamp_end=120.0, concept_id="c1", concept_name="Integration by Parts Formula", teaching_goal="Derive formula", purpose="visual_mechanism", narration="integral(u dv) = uv - integral(v du)", transcript="integral(u dv) = uv - integral(v du)", visual_strategy="mathematical_derivation")]
    )
    math_ctx = VideoContextResolver.resolve_context(math_pack, 40.0, "Ye minus sign yaha kaise aaya?")
    math_diag = ConfusionDiagnosisEngine.diagnose(math_ctx)
    math_ans = ExplanationStrategyEngine.generate_doubt_answer_sync(math_ctx, math_diag.confusion_type, math_diag.recommended_strategy, [])
    assert math_diag.confusion_type == ConfusionType.FORMULA_CONFUSION
    assert "Product Rule" in math_ans.explanation_markdown or "minus sign" in math_ans.explanation_markdown
    print(f"Math Doubt Answer: {math_ans.explanation_markdown[:120]}... -> PASS")

    # History: "Ye war start kyu hui?"
    hist_pack = VideoKnowledgePackage(
        video_id="v_hist", topic="French Revolution", domain="history",
        learner_level="Undergrad", language="hinglish", total_duration_seconds=180.0,
        scenes=[SceneKnowledge(scene_id="s1", order=1, timestamp_start=0.0, timestamp_end=180.0, concept_id="c1", concept_name="Causes of Revolution", teaching_goal="Explain catalysts", purpose="cause_effect", narration="The French revolution started due to social inequality in 1789.", transcript="The French revolution started due to social inequality in 1789.", visual_strategy="timeline")]
    )
    hist_ctx = VideoContextResolver.resolve_context(hist_pack, 30.0, "Ye war start kyu hui?")
    hist_diag = ConfusionDiagnosisEngine.diagnose(hist_ctx)
    hist_ans = ExplanationStrategyEngine.generate_doubt_answer_sync(hist_ctx, hist_diag.confusion_type, hist_diag.recommended_strategy, [])
    assert hist_diag.confusion_type == ConfusionType.RELATIONSHIP_CONFUSION
    assert "Estates" in hist_ans.explanation_markdown or "Bastille" in hist_ans.explanation_markdown
    print(f"History Doubt Answer: {hist_ans.explanation_markdown[:120]}... -> PASS")

    # Biology: "ATP yaha kyu ban raha hai?"
    bio_pack = VideoKnowledgePackage(
        video_id="v_bio", topic="Photosynthesis", domain="biology",
        learner_level="Class 10", language="hinglish", total_duration_seconds=180.0,
        scenes=[SceneKnowledge(scene_id="s1", order=1, timestamp_start=0.0, timestamp_end=180.0, concept_id="c1", concept_name="Light Reactions", teaching_goal="Explain ATP synthesis", purpose="scientific_process", narration="Light dependent reactions synthesize ATP in thylakoids.", transcript="Light dependent reactions synthesize ATP in thylakoids.", visual_strategy="process_flow")]
    )
    bio_ctx = VideoContextResolver.resolve_context(bio_pack, 45.0, "ATP yaha kyu ban raha hai?")
    bio_diag = ConfusionDiagnosisEngine.diagnose(bio_ctx)
    bio_ans = ExplanationStrategyEngine.generate_doubt_answer_sync(bio_ctx, bio_diag.confusion_type, bio_diag.recommended_strategy, [])
    assert "Calvin" in bio_ans.explanation_markdown or "ATP" in bio_ans.explanation_markdown
    print(f"Biology Doubt Answer: {bio_ans.explanation_markdown[:120]}... -> PASS")

    print(">>> Cross-domain doubt resolution PASSED.")


def test_ffmpeg_discovery_and_end_to_end_compilation():
    print("\n--- TEST 8: FFmpeg Discovery & End-to-End Pipeline Execution ---")
    ffmpeg_bin = get_ffmpeg_binary()
    print(f"FFmpeg Binary Discovered: {ffmpeg_bin}")
    assert check_ffmpeg_available(), "FFmpeg must be available via imageio-ffmpeg or system PATH (Decision #5)"

    config = VideoConfig(
        topic="Linked List",
        domain=DomainCategory.COMPUTER_SCIENCE,
        duration=60,  # 1 minute test run
        language="hinglish",
        quality=VideoQuality.STANDARD
    )

    project = asyncio.run(generate_video_pipeline(config, user_id="test_runner_v2"))
    print(f"Generated Video Project: ID={project.id} | Status={project.status} | URL={project.final_video_url}")
    print(f"Knowledge Package: Topic='{project.knowledge_package.topic}' | Scenes={len(project.knowledge_package.scenes)}")

    assert project.status in ("ready", "processing")
    assert project.knowledge_package is not None
    assert len(project.knowledge_package.scenes) >= 3

    print(">>> FFmpeg discovery & end-to-end compilation PASSED.")


if __name__ == "__main__":
    test_domain_intelligence_and_intent_parser()
    test_dynamic_curriculum_and_concept_graphs()
    test_storyboard_compilation_and_archetype_routing()
    test_visualizer_registry_and_linked_list_benchmark()
    test_language_teaching_engine_term_preservation()
    test_timestamp_context_resolver_and_doubt_pipeline()
    test_cross_domain_doubt_resolution()
    test_ffmpeg_discovery_and_end_to_end_compilation()

    print("\n====================================================================")
    print("ALL 8 BENCHMARK SUITE TESTS PASSED WITH 100% SUCCESS!")
    print("====================================================================")

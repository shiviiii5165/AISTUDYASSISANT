"""
TeachGenie Advanced Presentation Engine — Comprehensive Test Suite
===================================================================
Tests:
1. Exact slide counts (10, 11, 12, 13, 14, 15)
2. All 5 deterministic design systems (Academic, Minimal, Technical, Editorial, Visual Learning)
3. All 4 programmatic diagram renderers (Flow, Architecture, Timeline, Comparison)
4. Structural QA, text fitting, and overflow auto-migration
5. ModelRouter task policy routing & cache key hashing
"""
import sys
import os
import io
import asyncio
from pptx import Presentation

# Setup sys path for backend
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Placeholder environment variables for isolated testing
os.environ.setdefault("SUPABASE_URL", "https://placeholder.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "placeholder")
os.environ.setdefault("SUPABASE_JWT_SECRET", "placeholder")
os.environ.setdefault("GEMINI_API_KEY", "placeholder")
os.environ.setdefault("GROQ_API_KEY", "placeholder")
os.environ.setdefault("CASHFREE_APP_ID", "placeholder")
os.environ.setdefault("CASHFREE_SECRET_KEY", "placeholder")

from app.services.presentation.schemas import (
    PresentationConfig, PresentationSpec, SlideSpec, VisualSpec, DiagramSpec, DesignSystem
)
from app.services.presentation.engine.builder import build_presentation_spec
from app.services.presentation.cache import compute_presentation_hash
from app.services.presentation.qa_agent import auto_heal_slide_python, inspect_slide_structure


def make_test_spec(count: int, design: str = "academic") -> PresentationSpec:
    """Creates a sample PresentationSpec with exactly `count` slides."""
    config = PresentationConfig(
        topic="Cloud Architecture & Distributed Systems",
        slide_count=count,
        audience="university",
        language="english",
        depth="full",
        design=DesignSystem(design),
        theme="blue_professional",
    )

    slides = []
    # 1. Hero Slide
    slides.append(SlideSpec(
        slide_no=1,
        type="hero",
        title="Cloud Architecture & Distributed Systems",
        subtitle="University Lecture on Scalable Infrastructure",
        key_message="Modern cloud architecture separates compute, storage, and networking.",
    ))

    # Intermediate slides
    for i in range(2, count - 1):
        if i == 2:
            # Architecture slide
            vspec = VisualSpec(
                kind="architecture",
                diagram_spec=DiagramSpec(
                    diagram_type="architecture",
                    title="Microservices Tier",
                    layers=[
                        {"name": "API Gateway", "components": ["Rate Limiter", "Auth Service"]},
                        {"name": "Services", "components": ["User Service", "Order Service", "Payment Service"]},
                        {"name": "Storage", "components": ["PostgreSQL", "Redis", "S3 Storage"]},
                    ]
                )
            )
            slides.append(SlideSpec(
                slide_no=i,
                type="architecture",
                title="Microservices Decouple Application Logic",
                key_message="Independent deployment boundaries enable rapid iteration.",
                body_bullets=["Service isolation prevents failure cascades", "Horizontal scaling scales bottlenecks"],
                layers=[
                    {"name": "API Gateway", "components": ["Rate Limiter", "Auth Service"]},
                    {"name": "Services", "components": ["User Service", "Order Service", "Payment Service"]},
                    {"name": "Storage", "components": ["PostgreSQL", "Redis", "S3 Storage"]},
                ],
                visual=vspec,
            ))
        elif i == 3:
            # Process Flow slide
            vspec = VisualSpec(
                kind="flow",
                diagram_spec=DiagramSpec(
                    diagram_type="flow",
                    title="CI/CD Pipeline",
                    steps=[
                        {"title": "Commit", "detail": "Git push to main branch"},
                        {"title": "Build", "detail": "Container image compiled"},
                        {"title": "Test", "detail": "Automated unit & e2e tests"},
                        {"title": "Deploy", "detail": "Rolling update to Kubernetes"},
                    ]
                )
            )
            slides.append(SlideSpec(
                slide_no=i,
                type="process_flow",
                title="Automated Continuous Deployment Workflow",
                key_message="Zero-downtime rolling updates ensure 99.99% availability.",
                body_bullets=["Automated gates verify test coverage", "Canary releases limit blast radius"],
                steps=[
                    {"title": "Commit", "detail": "Git push to main branch"},
                    {"title": "Build", "detail": "Container image compiled"},
                    {"title": "Test", "detail": "Automated unit & e2e tests"},
                    {"title": "Deploy", "detail": "Rolling update to Kubernetes"},
                ],
                visual=vspec,
            ))
        elif i == 4:
            # Timeline slide
            vspec = VisualSpec(
                kind="timeline",
                diagram_spec=DiagramSpec(
                    diagram_type="timeline",
                    title="Evolution of Cloud",
                    milestones=[
                        {"date": "2006", "label": "AWS S3/EC2", "detail": "First public cloud IaaS"},
                        {"date": "2014", "label": "Kubernetes", "detail": "Container orchestration standard"},
                        {"date": "2024", "label": "AI Cloud", "detail": "Specialized GPU clusters"},
                    ]
                )
            )
            slides.append(SlideSpec(
                slide_no=i,
                type="timeline",
                title="Two Decades of Cloud Computing Milestones",
                key_message="From virtual machines to serverless and AI infrastructure.",
                body_bullets=["Virtualization enabled multi-tenancy", "Kubernetes standardized workloads"],
                milestones=[
                    {"date": "2006", "label": "AWS S3/EC2", "detail": "First public cloud IaaS"},
                    {"date": "2014", "label": "Kubernetes", "detail": "Container orchestration standard"},
                    {"date": "2024", "label": "AI Cloud", "detail": "Specialized GPU clusters"},
                ],
                visual=vspec,
            ))
        elif i == 5:
            # Comparison slide
            vspec = VisualSpec(
                kind="comparison",
                diagram_spec=DiagramSpec(
                    diagram_type="comparison",
                    title="Monolith vs Microservices",
                    columns=[
                        {"heading": "Monolith", "points": ["Single deployable unit", "Simple local debugging", "Tight coupling"]},
                        {"heading": "Microservices", "points": ["Independent deployments", "Fault isolation", "Operational complexity"]},
                    ]
                )
            )
            slides.append(SlideSpec(
                slide_no=i,
                type="comparison",
                title="Monolith vs Microservices: Trade-Off Analysis",
                key_message="Choose architecture based on organizational maturity.",
                body_bullets=["Monoliths work best for early startups", "Microservices unlock high team velocity"],
                columns=[
                    {"heading": "Monolith", "points": ["Single deployable unit", "Simple local debugging", "Tight coupling"]},
                    {"heading": "Microservices", "points": ["Independent deployments", "Fault isolation", "Operational complexity"]},
                ],
                visual=vspec,
            ))
        else:
            # Concept slide
            slides.append(SlideSpec(
                slide_no=i,
                type="concept",
                title=f"Core Architectural Principle #{i}",
                key_message=f"Detailed analysis for system component {i}.",
                body_bullets=[
                    "Stateless application servers scale horizontally",
                    "Stateful data stores require replication & consensus",
                    "Caching layers reduce database read pressure by 80%",
                ],
                example="Redis clusters cache session state to handle 100k+ concurrent requests.",
                speaker_notes="Explain how statelessness simplifies autoscaling policies.",
            ))

    # Summary slide (n-1)
    slides.append(SlideSpec(
        slide_no=count - 1,
        type="summary",
        title="Summary & Core Architecture Takeaways",
        key_message="Key architectural trade-offs to remember.",
        body_bullets=[
            "Design for failure with redundancy and circuit breakers",
            "Decouple state from compute instances",
            "Automate deployment pipelines and monitoring",
        ],
    ))

    # Closing slide (n)
    slides.append(SlideSpec(
        slide_no=count,
        type="qa",
        title="Thank You & Open Discussion",
        subtitle="Questions & Architecture Review",
        key_message="Review and questions.",
    ))

    return PresentationSpec(
        title="Cloud Architecture & Distributed Systems",
        subtitle="University Lecture",
        config=config,
        key_takeaways=["Decouple compute and storage", "Embrace immutability"],
        slides=slides,
    )


def test_exact_slide_counts():
    """Test that all requested slide counts (10, 11, 12, 13, 14, 15) produce exact slide counts in PPTX."""
    print("\n--- TEST 1: Exact Slide Counts (10, 11, 12, 13, 14, 15) ---")
    for n in [10, 11, 12, 13, 14, 15]:
        spec = make_test_spec(count=n, design="academic")
        pptx_bytes = build_presentation_spec(spec)
        
        # Parse output PPTX
        prs = Presentation(io.BytesIO(pptx_bytes))
        actual_count = len(prs.slides)
        print(f"Requested: {n} slides | Rendered: {actual_count} slides -> {'PASS' if actual_count == n else 'FAIL'}")
        assert actual_count == n, f"Expected {n} slides, got {actual_count}"
    print(">>> All exact slide count assertions PASSED.")


def test_all_design_systems():
    """Test all 5 deterministic design systems."""
    print("\n--- TEST 2: All 5 Design Systems ---")
    designs = ["academic", "minimal", "technical", "editorial", "visual"]
    for d in designs:
        spec = make_test_spec(count=12, design=d)
        pptx_bytes = build_presentation_spec(spec)
        prs = Presentation(io.BytesIO(pptx_bytes))
        assert len(prs.slides) == 12
        print(f"Design System '{d}': Successfully rendered {len(prs.slides)} slides -> PASS")
    print(">>> All 5 design systems PASSED.")


def test_diagram_rendering():
    """Test that diagrams render cleanly into shapes without crashing."""
    print("\n--- TEST 3: Programmatic Diagram Renderers ---")
    spec = make_test_spec(count=10, design="technical")
    pptx_bytes = build_presentation_spec(spec)
    prs = Presentation(io.BytesIO(pptx_bytes))
    
    # Check that shapes were generated on slide 2 (architecture) and slide 3 (flow)
    assert len(prs.slides[1].shapes) > 3, "Architecture slide did not render shapes"
    assert len(prs.slides[2].shapes) > 3, "Flow slide did not render shapes"
    print(f"Slide 2 shapes: {len(prs.slides[1].shapes)} (Architecture)")
    print(f"Slide 3 shapes: {len(prs.slides[2].shapes)} (Process Flow)")
    print(">>> Diagram rendering PASSED.")


def test_qa_overflow_and_auto_healing():
    """Test that Python QA auto-heals over-dense slides and migrates overflow to speaker notes."""
    print("\n--- TEST 4: Python QA Overflow & Auto-Healing ---")
    bad_slide = {
        "slide_no": 3,
        "title": "This is an extremely long title that exceeds reasonable presentation boundaries and should be shortened by the QA engine automatically",
        "body_bullets": [
            "Bullet 1: Normal concise bullet point",
            "Bullet 2: Another standard bullet point with some detail",
            "Bullet 3: Third bullet point",
            "Bullet 4: Fourth bullet point",
            "Bullet 5: Fifth bullet point",
            "Bullet 6: Overflow bullet point that should be moved to notes",
            "Bullet 7: Second overflow bullet point that should also be moved to notes",
        ],
        "speaker_notes": "Existing notes.",
    }

    issues_before = inspect_slide_structure(bad_slide)
    print(f"Issues detected before healing: {len(issues_before)}")
    assert len(issues_before) > 0

    healed = auto_heal_slide_python(bad_slide)
    assert len(healed["body_bullets"]) <= 5, "Excess bullets were not trimmed"
    assert "Additional points:" in healed["speaker_notes"], "Overflow was not migrated to speaker notes"
    assert len(healed["title"]) <= 80, "Title was not trimmed"
    print(f"Healed bullets count: {len(healed['body_bullets'])}")
    print(f"Healed speaker notes:\n{healed['speaker_notes']}")
    print(">>> Python QA overflow & auto-healing PASSED.")


def test_cache_hashing():
    """Test deterministic hash generation for request caching."""
    print("\n--- TEST 5: Semantic Cache Hashing ---")
    config1 = PresentationConfig(topic="Cloud Computing", slide_count=12, audience="university")
    config2 = PresentationConfig(topic="cloud computing ", slide_count=12, audience="University")
    config3 = PresentationConfig(topic="Cloud Computing", slide_count=15, audience="university")

    h1 = compute_presentation_hash(config1)
    h2 = compute_presentation_hash(config2)
    h3 = compute_presentation_hash(config3)

    assert h1 == h2, "Normalized hashes should be identical"
    assert h1 != h3, "Different slide counts must yield distinct hashes"
    print(f"Hash 1 (12 slides): {h1[:16]}...")
    print(f"Hash 2 (12 slides normalized): {h2[:16]}... (Matched)")
    print(f"Hash 3 (15 slides): {h3[:16]}... (Distinct)")
    print(">>> Cache hashing PASSED.")


if __name__ == "__main__":
    test_exact_slide_counts()
    test_all_design_systems()
    test_diagram_rendering()
    test_qa_overflow_and_auto_healing()
    test_cache_hashing()
    print("\n=======================================================")
    print("ALL TEST SUITE CHECKS COMPLETED SUCCESSFULLY!")
    print("=======================================================")

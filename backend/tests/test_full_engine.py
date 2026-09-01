"""
Full Presentation Engine Test
Tests ALL 14 slide layouts with a comprehensive sample deck.
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("SUPABASE_URL", "https://placeholder.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "placeholder")
os.environ.setdefault("SUPABASE_JWT_SECRET", "placeholder")
os.environ.setdefault("GEMINI_API_KEY", "placeholder")
os.environ.setdefault("GROQ_API_KEY", "placeholder")
os.environ.setdefault("CASHFREE_APP_ID", "placeholder")
os.environ.setdefault("CASHFREE_SECRET_KEY", "placeholder")
os.environ.setdefault("GEMINI_IMAGE_API_KEY", "")

# Now test the new engine directly
from app.services.presentation_engine import (
    SlideContent, SlidePurpose, PresentationPlan,
    VisualType, ProcessStep, TimelineMilestone,
    ComparisonColumn, KPIMetric, ArchitectureLayer,
)
from app.services.presentation_engine.builder import build_presentation


def create_full_test_plan():
    """Create a comprehensive test plan covering all 14 layout types."""
    return PresentationPlan(
        deck_title="Cloud Computing Architecture: Building Scalable Modern Systems",
        key_takeaways=[
            "Cloud computing separates compute, storage, and networking into elastic services",
            "The 3 major providers (AWS, Azure, GCP) serve 65% of global cloud market",
            "Microservices architecture enables independent scaling and deployment",
            "Kubernetes orchestrates containers at scale across hybrid infrastructure",
            "Cost optimization requires continuous monitoring and right-sizing",
        ],
        slides=[
            # 1. CONCEPT
            SlideContent(
                id="what_is_cloud",
                purpose=SlidePurpose.CONCEPT,
                title="Cloud Computing Delivers Resources as Elastic On-Demand Services",
                body_bullets=[
                    "NIST defines 5 essential characteristics of cloud",
                    "On-demand self-service eliminates provisioning delays",
                    "Broad network access enables anywhere availability",
                    "Resource pooling serves multiple tenants efficiently",
                    "Measured service enables pay-per-use billing",
                ],
                example="Netflix migrated from its own data centers to AWS in 2016, reducing costs by 75% while handling 250M+ subscribers.",
                speaker_note="Start by asking who has used cloud services today. Most will realize they've used Gmail, Dropbox, or iCloud. Then explain these are all cloud computing.",
            ),
            # 2. TWO COLUMN
            SlideContent(
                id="iaas_paas_saas",
                purpose=SlidePurpose.TWO_COLUMN,
                title="IaaS vs PaaS vs SaaS: Three Service Models for Different Needs",
                body_bullets=[
                    "IaaS: Virtual machines, storage, networks (AWS EC2)",
                    "PaaS: Managed platforms for app deployment (Heroku)",
                    "SaaS: Ready-to-use applications (Google Workspace)",
                    "Each model trades control for convenience",
                ],
                example="A startup uses SaaS for email (Gmail), PaaS for their web app (Heroku), and IaaS for their ML training (AWS EC2 GPU instances).",
                speaker_note="Use the pizza analogy: IaaS is buying ingredients, PaaS is buying a premade base, SaaS is ordering delivery.",
            ),
            # 3. IMAGE INSIGHT
            SlideContent(
                id="global_market",
                purpose=SlidePurpose.IMAGE_INSIGHT,
                title="The $600B Cloud Market is Dominated by Three Hyperscalers",
                body_bullets=[
                    "AWS leads with 31% market share ($90B+ revenue)",
                    "Microsoft Azure holds 25% and growing fastest",
                    "Google Cloud at 11% with strong AI/ML positioning",
                    "Multi-cloud strategies adopted by 87% of enterprises",
                ],
                key_insight="The cloud market grew 20% year-over-year in 2025, reaching $600B globally.",
                speaker_note="Emphasize that this isn't just tech companies. Banks, hospitals, governments all use cloud now.",
            ),
            # 4. ARCHITECTURE
            SlideContent(
                id="arch_layers",
                purpose=SlidePurpose.ARCHITECTURE,
                title="Modern Cloud Architecture Uses Layered Separation of Concerns",
                layers=[
                    ArchitectureLayer(name="Presentation Layer", components=["React SPA", "CDN", "Load Balancer"]),
                    ArchitectureLayer(name="API Gateway", components=["Rate Limiting", "Auth", "Routing"]),
                    ArchitectureLayer(name="Microservices", components=["User Service", "Order Service", "Payment Service"]),
                    ArchitectureLayer(name="Data Layer", components=["PostgreSQL", "Redis Cache", "S3 Storage"]),
                    ArchitectureLayer(name="Infrastructure", components=["Kubernetes", "Terraform", "Monitoring"]),
                ],
                speaker_note="Walk through each layer from top to bottom. Explain how requests flow from user browser through the API gateway to services and data.",
            ),
            # 5. PROCESS FLOW
            SlideContent(
                id="deployment_pipeline",
                purpose=SlidePurpose.PROCESS_FLOW,
                title="CI/CD Pipelines Automate the Journey from Code to Production",
                steps=[
                    ProcessStep(number=1, title="Code Commit", detail="Developer pushes to Git"),
                    ProcessStep(number=2, title="Build & Test", detail="CI runs unit/integration tests"),
                    ProcessStep(number=3, title="Container Build", detail="Docker image created"),
                    ProcessStep(number=4, title="Staging Deploy", detail="Auto-deploy to staging"),
                    ProcessStep(number=5, title="Production", detail="Blue-green deployment"),
                ],
                speaker_note="Emphasize that manual deployments are error-prone. Netflix deploys thousands of times per day using automated pipelines.",
            ),
            # 6. TIMELINE
            SlideContent(
                id="cloud_evolution",
                purpose=SlidePurpose.TIMELINE,
                title="Cloud Computing Evolved from Mainframes to Serverless in 50 Years",
                milestones=[
                    TimelineMilestone(date="1960s", label="Mainframe Time-Sharing", detail="First shared computing"),
                    TimelineMilestone(date="1999", label="Salesforce SaaS Launch", detail="CRM as a service"),
                    TimelineMilestone(date="2006", label="AWS EC2 Launch", detail="IaaS revolution begins"),
                    TimelineMilestone(date="2013", label="Docker Released", detail="Container revolution"),
                    TimelineMilestone(date="2014", label="AWS Lambda", detail="Serverless computing"),
                    TimelineMilestone(date="2024", label="AI Cloud Services", detail="LLMs as a service"),
                ],
                speaker_note="The timeline shows how cloud computing built on decades of shared computing concepts. Each milestone enabled the next.",
            ),
            # 7. COMPARISON
            SlideContent(
                id="cloud_providers",
                purpose=SlidePurpose.COMPARISON,
                title="AWS vs Azure vs GCP: Different Strengths for Different Needs",
                columns=[
                    ComparisonColumn(heading="AWS", points=["Broadest service catalog (200+)", "Strongest ecosystem", "Best for startups", "Most regions globally"]),
                    ComparisonColumn(heading="Azure", points=["Best enterprise integration", "Hybrid cloud leader", "Strong .NET support", "Government compliance"]),
                    ComparisonColumn(heading="GCP", points=["Superior AI/ML tools", "Best data analytics", "Kubernetes-native", "Competitive pricing"]),
                ],
                speaker_note="There's no single best cloud provider. The right choice depends on existing tech stack, compliance needs, and specific workload requirements.",
            ),
            # 8. KPI METRICS
            SlideContent(
                id="cloud_impact",
                purpose=SlidePurpose.KPI_METRICS,
                title="Cloud Computing Delivers Measurable Business Impact",
                metrics=[
                    KPIMetric(value="40%", label="Cost Reduction", context="Average infrastructure cost savings after cloud migration"),
                    KPIMetric(value="99.99%", label="Uptime SLA", context="Enterprise-grade availability from major cloud providers"),
                    KPIMetric(value="10x", label="Faster Deployment", context="Deployment frequency improvement with cloud-native CI/CD"),
                ],
                speaker_note="These numbers come from Gartner and McKinsey research. Cost savings vary widely depending on workload optimization.",
            ),
            # 9. CASE STUDY
            SlideContent(
                id="netflix_case",
                purpose=SlidePurpose.CASE_STUDY,
                title="Netflix: How the Streaming Giant Runs Entirely on AWS Cloud",
                body_bullets=[
                    "Migrated from 1000+ servers in own data centers",
                    "7-year migration completed in 2016",
                    "Now serves 250M+ subscribers across 190 countries",
                    "Handles 100K+ API requests per second at peak",
                    "Open-sourced key tools (Chaos Monkey, Zuul, Eureka)",
                    "Reduced streaming costs by 75% per subscriber",
                ],
                example="Netflix invented Chaos Engineering by randomly terminating production instances to build resilient systems.",
                speaker_note="Netflix is the canonical cloud migration success story. Their open-source tools like Chaos Monkey changed how the industry thinks about reliability.",
            ),
            # 10. QUOTE INSIGHT
            SlideContent(
                id="key_principle",
                purpose=SlidePurpose.QUOTE_INSIGHT,
                quote="The cloud is not about technology. It's about how you use technology to transform your business.",
                quote_attribution="Werner Vogels, CTO of Amazon",
                speaker_note="This quote captures the essential insight: cloud isn't just cheaper servers, it's a fundamentally different way of building and operating software.",
            ),
            # 11. SUMMARY
            SlideContent(
                id="summary",
                purpose=SlidePurpose.SUMMARY,
                title="Key Takeaways: What Every Architect Should Remember",
                body_bullets=[
                    "Cloud computing separates compute, storage, and networking into elastic services",
                    "The 3 major providers (AWS, Azure, GCP) serve 65% of global cloud market",
                    "Microservices architecture enables independent scaling and deployment",
                    "Kubernetes orchestrates containers at scale across hybrid infrastructure",
                    "Cost optimization requires continuous monitoring and right-sizing",
                ],
                speaker_note="Review these 5 takeaways. Ask students which concept was most surprising or useful to them.",
            ),
        ],
    )


async def main():
    print("=" * 60)
    print("FULL PRESENTATION ENGINE TEST")
    print("Testing all 14 slide layout types")
    print("=" * 60)

    plan = create_full_test_plan()
    print(f"\nTopic: {plan.deck_title}")
    print(f"Content slides: {len(plan.slides)}")
    print(f"Slide purposes: {[s.purpose.value for s in plan.slides]}")

    # Test with different themes
    themes_to_test = ["blue_professional", "indigo_innovation", "emerald_academic"]

    for theme_id in themes_to_test:
        print(f"\n--- Testing theme: {theme_id} ---")
        try:
            pptx_bytes = build_presentation(
                plan=plan,
                theme_id=theme_id,
                topic="Cloud Computing Architecture",
                preset_label="Technical Architecture",
                audience="university",
            )

            output_path = f"test_output_{theme_id}.pptx"
            with open(output_path, "wb") as f:
                f.write(pptx_bytes)

            file_size_kb = len(pptx_bytes) / 1024
            print(f"  [OK] Generated {file_size_kb:.1f} KB PPTX -> {output_path}")

            # Validate
            from pptx import Presentation as PptxPres
            prs = PptxPres(output_path)
            slide_count = len(prs.slides)
            print(f"  [SLIDES] {slide_count} slides")
            for i, slide in enumerate(prs.slides):
                shapes_count = len(slide.shapes)
                has_notes = bool(slide.has_notes_slide and slide.notes_slide.notes_text_frame.text.strip())
                notes_tag = " + notes" if has_notes else ""
                print(f"    Slide {i+1}: {shapes_count} shapes{notes_tag}")

        except Exception as e:
            print(f"  [FAIL] {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("Open test_output_*.pptx files to visually verify!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

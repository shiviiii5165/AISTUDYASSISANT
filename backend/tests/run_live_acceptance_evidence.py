import asyncio
import time
import json
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.lesson_resources.schemas import (
    ResourceIntentProfile, ResourceType, ProviderDiagnosticState
)
from app.services.lesson_resources.intent_profile import IntentProfileBuilder
from app.services.lesson_resources.service import StageResourceIntelligenceService
from app.services.lesson_planner.vnext.resources.coding_engine import CodingResourceEngine
from app.services.lesson_planner.schemas import (
    RoadmapStage, StageArchetype, CanonicalDomain, TeachingIntent, ProductMode
)


BENCHMARK_TOPICS = [
    {
        "topic": "object and class in python",
        "stage_title": "Objects & Classes Overview",
        "learner_level": "B.Tech",
        "is_algo": False
    },
    {
        "topic": "Dynamic Programming",
        "stage_title": "0/1 Knapsack Problem",
        "learner_level": "B.Tech",
        "is_algo": True
    },
    {
        "topic": "Binary Search Tree",
        "stage_title": "BST Insertion and Deletion",
        "learner_level": "B.Tech",
        "is_algo": True
    },
    {
        "topic": "React Server Components",
        "stage_title": "Server vs Client Components Architecture",
        "learner_level": "B.Tech",
        "is_algo": False
    },
    {
        "topic": "Massive MIMO",
        "stage_title": "Beamforming and Spatial Multiplexing",
        "learner_level": "B.Tech",
        "is_algo": False
    }
]


async def run_acceptance():
    report_data = []

    for b in BENCHMARK_TOPICS:
        topic = b["topic"]
        stage_title = b["stage_title"]
        level = b["learner_level"]
        is_algo = b["is_algo"]

        stage = RoadmapStage(
            id=f"stg_{abs(hash(topic)) % 10000}",
            concept_id="c_bench",
            title=stage_title,
            description=f"Detailed educational stage covering {stage_title} for {topic}",
            duration_minutes=20,
            archetype=StageArchetype.CODING if is_algo else StageArchetype.EXPLANATION
        )

        # 1. Resolve Profile & Context
        profile = IntentProfileBuilder.build(
            roadmap_id="rm_bench",
            stage_id=stage.id,
            topic=topic,
            stage_title=stage_title,
            learner_level=level
        )

        # 2. Test Coding Engine Provider Execution
        t0 = time.time()
        coding_cards, coding_diag = CodingResourceEngine.get_coding_resources_with_diagnostics(
            topic=topic,
            stage=stage,
            learner_proficiency="developing",
            context=profile.context
        )
        coding_latency = (time.time() - t0) * 1000

        # 3. Test Learning Materials API Execution
        t1 = time.time()
        materials_res = await StageResourceIntelligenceService.get_learning_materials(
            topic=topic,
            stage=stage,
            learner_level=level,
            refresh=True
        )
        materials_latency = (time.time() - t1) * 1000

        # Provider Diagnostics
        topic_summary = {
            "topic": topic,
            "stage_title": stage_title,
            "domain": profile.domain,
            "specialization": profile.specialization,
            "visible_categories": materials_res.visible_tabs,
            "coding_cards_count": len(coding_cards),
            "coding_diagnostics": coding_diag,
            "materials_count": {
                "academic_references": len(materials_res.categories.academic_references or []),
                "research_papers": len(materials_res.categories.research_papers or []),
                "documentation": len(materials_res.categories.documentation or []),
                "practice_coding": len(materials_res.categories.practice_coding or []),
                "guides_tutorials": len(materials_res.categories.guides_tutorials or [])
            },
            "research_papers_displayed": "research_papers" in materials_res.visible_tabs,
            "sample_cards": [
                {
                    "title": c.title,
                    "url": c.url,
                    "source": c.source_authority,
                    "why_recommended": c.why_recommended
                }
                for c in coding_cards[:3]
            ]
        }
        report_data.append(topic_summary)

    print(json.dumps(report_data, indent=2))


if __name__ == "__main__":
    asyncio.run(run_acceptance())

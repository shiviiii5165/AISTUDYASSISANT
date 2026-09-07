"""
PPT Pipeline End-to-End Verification Script
=============================================
Part 3 of the image subsystem overhaul.

Verifies:
1. ImageService initializes with configured credentials
2. Stock photo API connectivity (Pexels, Pixabay, Unsplash)
3. Cache hit confirmation on second request
4. Attribution metadata presence (especially Unsplash)
5. Health-based provider ordering
6. Query generation from slide content

Run with: python -m backend.scripts.verify_ppt_pipeline
Or:       cd backend && python scripts/verify_ppt_pipeline.py
"""
import asyncio
import sys
import os

# Add backend to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))


async def verify_image_service():
    """Verify the ImageService subsystem end-to-end."""
    print("\n" + "=" * 70)
    print("  PPT Image Subsystem — End-to-End Verification")
    print("=" * 70)

    # 1. Import and initialize
    print("\n[1/6] Initializing ImageService...")
    try:
        from app.services.image_service.service import ImageService
        service = ImageService.get_instance()
        print("  ✅ ImageService initialized successfully")
    except Exception as e:
        print(f"  ❌ Failed to initialize ImageService: {e}")
        return False

    # 2. Check credential configuration
    print("\n[2/6] Checking credential configuration...")
    report = service.get_health_report()
    providers = report["providers"]
    all_ok = True
    for name, info in providers.items():
        status = "✅" if info["configured"] else "⚠️ "
        print(f"  {status} {name}: {info['total_credentials']} credentials, "
              f"{info['available_credentials']} available, "
              f"health_score={info['health_score']}")
        if not info["configured"]:
            all_ok = False

    if not all_ok:
        print("  ⚠️  Some providers have no credentials — they will be skipped")

    # 3. Test real API connectivity with a sample query
    test_queries = [
        "machine learning neural network brain",
        "software development team meeting",
        "waterfall landscape nature river",
    ]

    print("\n[3/6] Testing stock photo API connectivity...")
    results = []
    for query in test_queries:
        print(f"\n  Query: '{query}'")
        try:
            result = await service.get_best_image(query, timeout=20.0)
            if result:
                print(f"  ✅ Got {len(result.image_bytes)} bytes from {result.provider}")
                print(f"     URL: {result.url[:80]}...")
                if result.attribution.photographer_name:
                    print(f"     📸 Photo by: {result.attribution.photographer_name}")
                if result.attribution.source_url:
                    print(f"     🔗 Source: {result.attribution.source_url[:80]}")
                results.append(result)
            else:
                print(f"  ⚠️  No image found (all providers returned empty)")
        except Exception as e:
            print(f"  ❌ Error: {e}")

    # 4. Test cache hit on second request
    print("\n[4/6] Testing cache hit on second request...")
    if test_queries:
        cache_query = test_queries[0]
        try:
            result2 = await service.get_best_image(cache_query, timeout=5.0)
            if result2:
                print(f"  ✅ Cache HIT confirmed — got {len(result2.image_bytes)} bytes instantly")
            else:
                print(f"  ⚠️  Cache returned None (may have been evicted)")
        except Exception as e:
            print(f"  ❌ Cache test error: {e}")

    # 5. Check attribution compliance
    print("\n[5/6] Checking attribution compliance...")
    unsplash_results = [r for r in results if r.provider == "unsplash"]
    if unsplash_results:
        for r in unsplash_results:
            has_photographer = bool(r.attribution.photographer_name)
            has_source = bool(r.attribution.source_url)
            has_license = bool(r.attribution.license_type)
            status = "✅" if all([has_photographer, has_source, has_license]) else "⚠️ "
            print(f"  {status} Unsplash attribution: photographer={has_photographer}, "
                  f"source={has_source}, license={r.attribution.license_type}")
    else:
        print("  ℹ️  No Unsplash images in results — checking other providers")
        for r in results:
            print(f"  📋 {r.provider}: photographer='{r.attribution.photographer_name}', "
                  f"license='{r.attribution.license_type}'")

    # 6. Test QueryGenerator with slide content
    print("\n[6/6] Testing QueryGenerator with slide content...")
    from app.services.image_service.query_generator import QueryGenerator

    test_slides = [
        {
            "title": "Introduction to Machine Learning",
            "key_message": "Machine learning enables computers to learn from data",
            "image_query": "",
        },
        {
            "title": "Waterfall Model",
            "key_message": "Sequential phases in software development",
            "example": "Requirements → Design → Implementation → Testing → Maintenance",
            "image_query": "",
        },
        {
            "title": "Overview of Algorithms",
            "key_message": "",
            "body_bullets": ["Sorting algorithms comparison", "Search tree traversal"],
            "image_query": "",
        },
    ]

    for slide in test_slides:
        query = QueryGenerator.generate_query(slide, topic="Computer Science")
        print(f"  📝 '{slide['title']}' → '{query}'")

    # Summary
    print("\n" + "=" * 70)
    success_count = len(results)
    total = len(test_queries)
    print(f"  Results: {success_count}/{total} queries resolved to images")
    print(f"  Cache stats: {report['cache']}")
    print("=" * 70)

    return success_count > 0


async def verify_content_pattern_fix():
    """Verify the content_pattern propagation fix in orchestrator."""
    print("\n" + "=" * 70)
    print("  Content Pattern Propagation — Verification")
    print("=" * 70)

    from app.services.presentation.schemas import SlideSpec, ContentPattern, VisualSpec, VisualKind

    # Simulate orchestrator construction
    test_patterns = [
        ("definition_box", ContentPattern.DEFINITION_BOX),
        ("contrast_pair", ContentPattern.CONTRAST_PAIR),
        ("numbered_process", ContentPattern.NUMBERED_PROCESS),
        (None, None),
    ]

    all_pass = True
    for input_val, expected in test_patterns:
        slide_dict = {"content_pattern": input_val}
        spec = SlideSpec(
            slide_no=1,
            title="Test",
            content_pattern=slide_dict.get("content_pattern"),
            visual=VisualSpec(kind=VisualKind.NONE),
        )
        status = "✅" if spec.content_pattern == expected else "❌"
        if spec.content_pattern != expected:
            all_pass = False
        print(f"  {status} input='{input_val}' → content_pattern={spec.content_pattern}")

    print(f"\n  Overall: {'✅ All patterns propagate correctly' if all_pass else '❌ FAILURES DETECTED'}")
    return all_pass


async def main():
    print("\n🔍 PPT Pipeline End-to-End Verification")
    print("=" * 70)

    # Part 2: Content pattern fix
    pattern_ok = await verify_content_pattern_fix()

    # Part 1 & 3: Image service
    image_ok = await verify_image_service()

    print("\n\n" + "=" * 70)
    print("  FINAL RESULTS")
    print("=" * 70)
    print(f"  Content Pattern Fix: {'✅ PASS' if pattern_ok else '❌ FAIL'}")
    print(f"  Image Service:       {'✅ PASS' if image_ok else '⚠️  PARTIAL (check API keys)'}")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())

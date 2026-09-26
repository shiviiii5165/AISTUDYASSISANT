"""
Test Suite: Source Reading MVP & SourceExtractionService
========================================================
Validates:
1. SSRF, Loopback, Link-Local & Metadata Defense (Zero Bypass)
2. Wikipedia MediaWiki Section Discovery (prop=tocdata, genuine anchors)
3. Provenance Preservation (Zero fabricated authors, dates, or quotations)
4. Cost & Credit Budget Enforcement (MVP 1-URL limit, credit accounting)
5. Controlled Failure Handling (Inaccessible/404/paywall URLs)
6. Feature-Flagged Librarian Isolation (Frozen path unchanged by default)
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock

from app.core.config import settings
from app.services.knowledge.source_extraction import (
    SourceExtractionService,
    ExtractionStatus,
    ExtractionBudget,
    validate_url_security,
    is_ip_disallowed,
    WikipediaMediaWikiExtractor
)
from app.agents.librarian import retrieve_context, LibrarianOutput, ChunkResult


# ══════════════════════════════════════════════════════════════════════════════
# 1. SSRF, LOOPBACK, & METADATA DESTINATION TESTS
# ══════════════════════════════════════════════════════════════════════════════

def test_disallowed_ip_filter():
    """Verify that private, loopback, link-local, and cloud metadata IPs are strictly blocked."""
    # Loopback
    assert is_ip_disallowed("127.0.0.1") is True
    assert is_ip_disallowed("127.0.1.1") is True
    assert is_ip_disallowed("::1") is True
    
    # Cloud Metadata
    assert is_ip_disallowed("169.254.169.254") is True
    assert is_ip_disallowed("169.254.1.1") is True
    
    # Private RFC 1918
    assert is_ip_disallowed("10.0.0.1") is True
    assert is_ip_disallowed("192.168.1.100") is True
    assert is_ip_disallowed("172.16.0.1") is True
    assert is_ip_disallowed("172.31.255.255") is True
    
    # Public IPs must pass
    assert is_ip_disallowed("8.8.8.8") is False
    assert is_ip_disallowed("1.1.1.1") is False


def test_url_security_validation_blocks_malicious_destinations():
    """Verify validate_url_security rejects SSRF, cloud metadata, and bad schemes."""
    # Non-http/https
    is_safe, _, err = validate_url_security("file:///etc/passwd")
    assert is_safe is False
    assert "scheme" in err.lower()
    
    is_safe, _, err = validate_url_security("ftp://example.com/data")
    assert is_safe is False
    
    # Loopback / Localhost
    is_safe, _, err = validate_url_security("http://localhost:8000/api")
    assert is_safe is False
    assert "internal hostname" in err.lower() or "prohibited" in err.lower()
    
    # Cloud metadata host
    is_safe, _, err = validate_url_security("http://169.254.169.254/latest/meta-data/")
    assert is_safe is False
    
    is_safe, _, err = validate_url_security("http://metadata.google.internal/computeMetadata/v1/")
    assert is_safe is False


def test_source_extraction_service_blocks_ssrf_attempt():
    """Verify extract_source returns FAILED_SSRF_BLOCKED without making external HTTP requests."""
    async def _run():
        res = await SourceExtractionService.extract_source("http://127.0.0.1:8080/admin")
        assert res.status == ExtractionStatus.FAILED_SSRF_BLOCKED
        assert res.credits_consumed == 0.0
        assert "ssrf" in res.error_detail.lower()
    asyncio.run(_run())


# ══════════════════════════════════════════════════════════════════════════════
# 2. MEDIAWIKI WIKIPEDIA SECTION LINKING TESTS
# ══════════════════════════════════════════════════════════════════════════════

def test_wikipedia_url_identification_and_title():
    """Verify title parsing from Wikipedia URLs."""
    url = "https://en.wikipedia.org/wiki/Photosynthesis"
    assert WikipediaMediaWikiExtractor.is_wikipedia_url(url) is True
    assert WikipediaMediaWikiExtractor.extract_page_title(url) == "Photosynthesis"

    url_encoded = "https://en.wikipedia.org/wiki/General_relativity#Overview"
    assert WikipediaMediaWikiExtractor.extract_page_title(url_encoded) == "General relativity"


def test_wikipedia_section_discovery_and_genuine_anchors():
    """Verify MediaWiki prop=tocdata extracts real anchors and matches section relevance."""
    async def _run():
        evidence = await SourceExtractionService.extract_source(
            "https://en.wikipedia.org/wiki/Photosynthesis",
            query="light dependent reactions and Z scheme",
            budget=ExtractionBudget(force_refresh=True)
        )
        assert evidence.status in (ExtractionStatus.SUCCESS, ExtractionStatus.CACHED)
        assert evidence.document_title == "Photosynthesis"
        assert evidence.extraction_method in ("official_api", "cache")
        assert evidence.credits_consumed == 0.0
        
        # Must have genuine section anchor (e.g. #Light-dependent_reactions or #Z_scheme)
        if evidence.section_anchor:
            assert evidence.section_anchor.startswith("#")
            assert evidence.canonical_url.endswith(evidence.section_anchor)
            # Must not fabricate PDF anchors
            assert ".pdf#" not in evidence.canonical_url
    asyncio.run(_run())


# ══════════════════════════════════════════════════════════════════════════════
# 3. PROVENANCE PRESERVATION & ZERO FABRICATION
# ══════════════════════════════════════════════════════════════════════════════

def test_provenance_fields_present_and_unfabricated():
    """Verify all required provenance metadata is tracked and unstated attributes remain None."""
    async def _run():
        evidence = await SourceExtractionService.extract_source(
            "https://en.wikipedia.org/wiki/Eigenvalues_and_eigenvectors",
            query="principal component analysis covariance matrix",
            budget=ExtractionBudget(force_refresh=True)
        )
        assert evidence.source_url.startswith("https://")
        assert evidence.canonical_url.startswith("https://")
        assert evidence.document_title != ""
        assert evidence.retrieval_timestamp != ""
        assert "T" in evidence.retrieval_timestamp  # ISO format
        assert evidence.extraction_method in ("official_api", "direct_http", "tavily_extract", "cache")
        
        # Wikipedia has no single author: author must be None or 'Wikipedia Contributors', not a fabricated personal name
        if evidence.author:
            assert "Wikipedia" in evidence.author
        assert evidence.publication_date is None  # Never fabricated
    asyncio.run(_run())


# ══════════════════════════════════════════════════════════════════════════════
# 4. COST BUDGET & CONTROLLED FAILURE TESTS
# ══════════════════════════════════════════════════════════════════════════════

def test_budget_defaults_and_caps():
    """Verify default budget enforces 1 URL per request and cost ceiling."""
    budget = ExtractionBudget()
    assert budget.max_urls_per_request == 1
    assert budget.max_credits_per_request == 0.4
    assert budget.max_content_length == 6000


def test_controlled_failure_on_inaccessible_url():
    """Verify invalid/404 URL returns structured failure status without crashing."""
    async def _run():
        res = await SourceExtractionService.extract_source(
            "https://httpbin.org/status/404",
            budget=ExtractionBudget(enable_tavily_fallback=False, force_refresh=True)
        )
        assert res.status in (ExtractionStatus.FAILED_HTTP_ERROR, ExtractionStatus.FAILED_EMPTY_CONTENT)
        assert res.credits_consumed == 0.0
        assert res.llm_context_text == ""
    asyncio.run(_run())


# ══════════════════════════════════════════════════════════════════════════════
# 5. FEATURE FLAGGED LIBRARIAN ISOLATION TESTS
# ══════════════════════════════════════════════════════════════════════════════

def test_librarian_default_path_unchanged_when_flag_disabled():
    """Verify that when LIBRARIAN_SOURCE_EXTRACTION_ENABLED is False, snippet behavior is strictly preserved."""
    async def _run():
        # Ensure default is False
        assert getattr(settings, "LIBRARIAN_SOURCE_EXTRACTION_ENABLED", False) is False

        mock_snippets = [
            {"title": "Test Source", "url": "https://example.com/test", "snippet": "A short test snippet."}
        ]
        with patch("app.agents.librarian.perform_web_search", return_value=mock_snippets):
            output = await retrieve_context(topic="Quantum computing gates", user_id="00000000-0000-0000-0000-000000000001")
            assert isinstance(output, LibrarianOutput)
            assert output.used_web_fallback is True
            # Chunk source must be standard 'web', not 'web_extracted'
            web_chunks = [c for c in output.context if c.source == "web"]
            assert len(web_chunks) > 0
            assert web_chunks[0].text == "A short test snippet."
    asyncio.run(_run())


# ══════════════════════════════════════════════════════════════════════════════
# 6. ENHANCED SECURITY & ACCESS CONTROL TESTS
# ══════════════════════════════════════════════════════════════════════════════

def test_port_validation_blocks_non_standard_ports():
    """Verify ports outside standard web ports (80, 443, 8080, 8443) are rejected."""
    # Disallowed ports (SSH, MySQL, Telnet, Redis)
    for port in [22, 23, 25, 3306, 6379, 27017]:
        is_safe, _, err = validate_url_security(f"http://example.com:{port}/path")
        assert is_safe is False
        assert "prohibited port" in err.lower()

    # Allowed ports
    for port in [80, 443, 8080, 8443]:
        is_safe, _, _ = validate_url_security(f"http://example.com:{port}/path")
        # May be safe if example.com resolves to public IP
        assert is_safe is True


def test_ipv6_private_and_link_local_blocked():
    """Verify IPv6 loopback, link-local, and unique local addresses are rejected."""
    assert is_ip_disallowed("::1") is True
    assert is_ip_disallowed("fe80::1") is True
    assert is_ip_disallowed("fc00::1") is True
    assert is_ip_disallowed("fd12:3456:789a:1::1") is True

    is_safe, _, err = validate_url_security("http://[::1]/admin")
    assert is_safe is False

    is_safe, _, err = validate_url_security("http://[fe80::1]/secret")
    assert is_safe is False


def test_redirect_to_private_ip_blocked():
    """Verify that a server redirecting to 127.0.0.1 or 169.254.169.254 is intercepted and blocked."""
    async def _run():
        # Mock httpx response that issues a 302 redirect to cloud metadata
        mock_resp = MagicMock()
        mock_resp.status_code = 302
        mock_resp.is_redirect = True
        mock_resp.headers = {"Location": "http://169.254.169.254/latest/meta-data/"}

        with patch("httpx.AsyncClient.get", return_value=mock_resp):
            res = await SourceExtractionService.extract_source(
                "http://example.com/redirect-to-metadata",
                budget=ExtractionBudget(force_refresh=True, enable_tavily_fallback=True)
            )
            assert res.status == ExtractionStatus.FAILED_SSRF_BLOCKED
            assert res.credits_consumed == 0.0
            assert "prohibited" in res.error_detail.lower() or "blocked" in res.error_detail.lower()
    asyncio.run(_run())


def test_paywall_and_403_never_trigger_scraping_fallback():
    """Verify that 403 Forbidden or paywalls NEVER trigger Tavily scraping fallback."""
    async def _run():
        # Test 403: must return FAILED_ACCESS_DENIED, not paywall
        with patch("httpx.AsyncClient.post") as mock_tavily_post:
            res = await SourceExtractionService.extract_source(
                "https://httpbin.org/status/403",
                budget=ExtractionBudget(force_refresh=True, enable_tavily_fallback=True)
            )
            assert res.status == ExtractionStatus.FAILED_ACCESS_DENIED
            assert res.credits_consumed == 0.0
            # Tavily Extract post must NEVER be called to bypass 403/paywall
            mock_tavily_post.assert_not_called()
    asyncio.run(_run())


def test_access_denied_distinct_from_paywall():
    """Verify HTTP 403 is labeled FAILED_ACCESS_DENIED, while confirmed paywall HTML is FAILED_PAYWALL_OR_AUTH."""
    async def _run():
        # 1. Ordinary 403 -> FAILED_ACCESS_DENIED
        mock_403 = MagicMock()
        mock_403.status_code = 403
        mock_403.is_redirect = False
        with patch("httpx.AsyncClient.get", return_value=mock_403):
            res_403 = await SourceExtractionService.extract_source(
                "http://example.com/forbidden-endpoint",
                budget=ExtractionBudget(force_refresh=True, enable_tavily_fallback=False)
            )
            assert res_403.status == ExtractionStatus.FAILED_ACCESS_DENIED
            assert "access denied" in res_403.error_detail.lower()

        # 2. HTTP 200 with paywall marker -> FAILED_PAYWALL_OR_AUTH
        mock_paywall = MagicMock()
        mock_paywall.status_code = 200
        mock_paywall.is_redirect = False
        mock_paywall.text = "<html><body><h1>Article</h1><p>Please subscribe to read the full article.</p></body></html>"
        with patch("httpx.AsyncClient.get", return_value=mock_paywall):
            res_paywall = await SourceExtractionService.extract_source(
                "http://example.com/paywalled-article",
                budget=ExtractionBudget(force_refresh=True, enable_tavily_fallback=False)
            )
            assert res_paywall.status == ExtractionStatus.FAILED_PAYWALL_OR_AUTH
            assert "paywall" in res_paywall.document_title.lower() or "paywall" in res_paywall.source_limitations[0]
    asyncio.run(_run())


def test_ipv4_mapped_ipv6_blocked():
    """Verify IPv4-mapped IPv6 addresses for loopback, metadata, and private nets are blocked."""
    assert is_ip_disallowed("::ffff:127.0.0.1") is True
    assert is_ip_disallowed("::ffff:169.254.169.254") is True
    assert is_ip_disallowed("::ffff:10.0.0.1") is True
    assert is_ip_disallowed("::ffff:192.168.1.1") is True


def test_unrelated_content_rejected_by_relevance_threshold():
    """Verify that text with zero or sub-threshold topical overlap yields 0 passages."""
    from app.services.knowledge.source_extraction import extract_relevant_passages
    
    unrelated_text = (
        "Welcome to the Minnesota translation and language interpretation services directory. "
        "We provide on-site and remote spoken language translation for business and travel. "
        "Contact our Minneapolis office for commercial rates and certified translation quotes."
    )
    query = "Python Global Interpreter Lock GIL PEP 703 free threading thread switching"
    
    passages = extract_relevant_passages(unrelated_text, query, min_relevance_threshold=0.12)
    assert len(passages) == 0, f"Expected 0 passages for unrelated text, got {len(passages)}"


def test_evidence_quality_gate():
    """Verify EvidenceQualityGate admits relevant high-quality evidence and rejects ungrounded/failed evidence."""
    from app.services.knowledge.source_extraction import EvidenceQualityGate, ExtractedPassage, ExtractedSourceEvidence
    from datetime import datetime, timezone

    now_iso = datetime.now(timezone.utc).isoformat()

    # Case 1: High quality matching evidence -> Admitted
    good_evidence = ExtractedSourceEvidence(
        source_url="https://en.wikipedia.org/wiki/Photoelectric_effect",
        canonical_url="https://en.wikipedia.org/wiki/Photoelectric_effect#Mathematical_description",
        document_title="Photoelectric effect",
        retrieval_timestamp=now_iso,
        extraction_method="official_api",
        status=ExtractionStatus.SUCCESS,
        relevant_passages=[
            ExtractedPassage(
                text="In the photoelectric effect, electrons are emitted when light of frequency f exceeds the threshold. The maximum kinetic energy is E = h*f - phi where phi is the work function.",
                char_offset=100,
                relevance_score=0.45
            )
        ]
    )
    admitted, reason = EvidenceQualityGate.evaluate_admission(good_evidence, "photoelectric effect work function equation Einstein")
    assert admitted is True
    assert "admitted" in reason

    # Case 2: Failed extraction status -> Rejected
    failed_evidence = ExtractedSourceEvidence(
        source_url="https://example.com/403",
        canonical_url="https://example.com/403",
        document_title="HTTP 403 Access Restricted",
        retrieval_timestamp=now_iso,
        extraction_method="direct_http",
        status=ExtractionStatus.FAILED_ACCESS_DENIED,
        relevant_passages=[]
    )
    admitted, reason = EvidenceQualityGate.evaluate_admission(failed_evidence, "photoelectric effect work function")
    assert admitted is False
    assert "rejected_status" in reason

    # Case 3: Low relevance passage -> Rejected
    low_rel_evidence = ExtractedSourceEvidence(
        source_url="https://example.com/unrelated",
        canonical_url="https://example.com/unrelated",
        document_title="Travel Guide",
        retrieval_timestamp=now_iso,
        extraction_method="direct_http",
        status=ExtractionStatus.SUCCESS,
        relevant_passages=[
            ExtractedPassage(
                text="Welcome to the summer travel guide for Minneapolis lakes and park attractions. Explore bike trails and local food festivals across the metropolitan area.",
                char_offset=0,
                relevance_score=0.05
            )
        ]
    )
    admitted, reason = EvidenceQualityGate.evaluate_admission(low_rel_evidence, "photoelectric effect work function")
    assert admitted is False
    assert "rejected_low_relevance" in reason

    # Case 4: Short stub passage -> Rejected
    stub_evidence = ExtractedSourceEvidence(
        source_url="https://example.com/stub",
        canonical_url="https://example.com/stub",
        document_title="Stub Page",
        retrieval_timestamp=now_iso,
        extraction_method="direct_http",
        status=ExtractionStatus.SUCCESS,
        relevant_passages=[
            ExtractedPassage(
                text="Short stub text.",
                char_offset=0,
                relevance_score=0.50
            )
        ]
    )
    admitted, reason = EvidenceQualityGate.evaluate_admission(stub_evidence, "photoelectric effect work function")
    assert admitted is False
    assert "rejected_passage_too_short" in reason


def test_canary_activation_and_telemetry_isolation():
    """Verify internal canary configuration enables extraction only for designated accounts/environments."""
    import json
    from app.services.knowledge.source_extraction_canary import canary_tracker

    orig_enabled = settings.LIBRARIAN_SOURCE_EXTRACTION_ENABLED
    orig_users = settings.LIBRARIAN_SOURCE_EXTRACTION_CANARY_USERS
    orig_env = settings.ENVIRONMENT

    try:
        # 1. Default configuration: canary inactive for unlisted user
        settings.LIBRARIAN_SOURCE_EXTRACTION_ENABLED = False
        settings.LIBRARIAN_SOURCE_EXTRACTION_CANARY_USERS = "test-canary-user-1,test-canary-user-2"
        settings.ENVIRONMENT = "development"

        assert settings.is_source_extraction_canary_active(user_id="general-user-123") is False
        assert settings.is_source_extraction_canary_active(user_id=None) is False

        # 2. Canary user activated
        assert settings.is_source_extraction_canary_active(user_id="test-canary-user-1") is True
        assert settings.is_source_extraction_canary_active(user_id="TEST-CANARY-USER-2") is True

        # 3. Staging environment activated
        settings.ENVIRONMENT = "staging"
        assert settings.is_source_extraction_canary_active(user_id="any-user-in-staging") is True

        # 4. Telemetry logging does not leak sensitive information
        canary_tracker.record_event(
            url="https://en.wikipedia.org/wiki/Photosynthesis?auth_token=secret123",
            extraction_method="official_api",
            is_cached=True,
            admitted=True,
            gate_reason="admitted_high_quality_evidence",
            passage_relevance=0.85,
            snippet_fallback_retained=False,
            claim_support=1.0,
            citation_valid=True,
            extraction_latency_ms=12.5,
            total_latency_ms=15.0,
            credits_consumed=0.0
        )
        last_event = canary_tracker.events[-1]
        assert last_event["source_domain"] == "en.wikipedia.org"
        assert "secret123" not in json.dumps(last_event)
    finally:
        settings.LIBRARIAN_SOURCE_EXTRACTION_ENABLED = orig_enabled
        settings.LIBRARIAN_SOURCE_EXTRACTION_CANARY_USERS = orig_users
        settings.ENVIRONMENT = orig_env




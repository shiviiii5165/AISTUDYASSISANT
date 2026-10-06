"""
LearnByGenie Source Reading & Extraction Service (Additive MVP)
============================================================
Provides reliable, cost-controlled access to relevant passages from permitted
public educational sources without commercial scrapers or third-party proxy rotators.

Hierarchy:
1. Official source APIs (e.g. MediaWiki Wikipedia parse & tocdata, arXiv) -> 0.0 credits
2. Direct permitted public-page fetch (with strict SSRF & DNS rebinding protection) -> 0.0 credits
3. Metered Tavily Extract fallback (for verified educational domains requiring JS rendering) -> 0.2 credits/URL
4. Explicit extraction failure (structured enum; never fabricates text or bypasses paywalls)
"""

import os
import re
import time
import json
import socket
import asyncio
import logging
import hashlib
import ipaddress
import urllib.parse
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

import httpx
from pydantic import BaseModel, Field

from app.core.config import settings

logger = logging.getLogger("learnbygenie.knowledge.source_extraction")

# Storage directory for bounded extracted content cache
_CACHE_DIR = Path(".cache/source_extractions")


# ══════════════════════════════════════════════════════════════════════════════
# ENUMS & DATA MODELS
# ══════════════════════════════════════════════════════════════════════════════

class ExtractionStatus(str, Enum):
    SUCCESS = "success"
    CACHED = "cached"
    FAILED_TIMEOUT = "failed_timeout"
    FAILED_HTTP_ERROR = "failed_http_error"
    FAILED_ACCESS_DENIED = "failed_access_denied"
    FAILED_PAYWALL_OR_AUTH = "failed_paywall_or_auth"
    FAILED_SSRF_BLOCKED = "failed_ssrf_blocked"
    FAILED_DOMAIN_NOT_PERMITTED = "failed_domain_not_permitted"
    FAILED_EMPTY_CONTENT = "failed_empty_content"
    BUDGET_EXCEEDED = "budget_exceeded"
    PROVIDER_ERROR = "provider_error"


class ExtractedPassage(BaseModel):
    """A focused passage extracted from the source for citation grounding."""
    text: str = Field(..., description="Verbatim extracted passage text.")
    char_offset: int = Field(0, description="Character offset within extracted body.")
    location_or_section: Optional[str] = Field(None, description="Section title or anchor where passage appears.")
    relevance_score: float = Field(0.0, description="Computed relevance score to query.")


class ExtractedSourceEvidence(BaseModel):
    """
    Immutable evidence record representing an extracted educational source.
    Does NOT treat retrieved text as automatically verified truth.
    Does NOT fabricate missing metadata.
    """
    source_url: str = Field(..., description="Original requested URL.")
    canonical_url: str = Field(..., description="Resolved canonical URL (including section anchor if applicable).")
    document_title: str = Field(..., description="Verified document title.")
    author: Optional[str] = Field(None, description="Author, channel, or publishing org if genuinely present.")
    publication_date: Optional[str] = Field(None, description="Publication date if genuinely present.")
    retrieval_timestamp: str = Field(..., description="ISO-8601 UTC retrieval timestamp.")
    location_or_section: Optional[str] = Field(None, description="Section heading or document location.")
    section_anchor: Optional[str] = Field(None, description="Genuine anchor fragment (e.g. #Overview).")
    extraction_method: str = Field(..., description="'official_api', 'direct_http', 'tavily_extract', or 'cache'.")
    status: ExtractionStatus = Field(..., description="Final extraction outcome.")
    credits_consumed: float = Field(0.0, description="Tavily or third-party credits consumed (0.0 for official/direct).")
    latency_ms: float = Field(0.0, description="Elapsed extraction time in milliseconds.")
    relevant_passages: List[ExtractedPassage] = Field(default_factory=list, description="Top relevant text passages.")
    llm_context_text: str = Field("", description="Bounded context string formatted for LLM consumption.")
    source_limitations: List[str] = Field(default_factory=list, description="Honest constraints (e.g. 'context_truncated_to_6000_chars').")
    error_detail: Optional[str] = Field(None, description="Structured failure message if extraction failed.")


class ExtractionBudget(BaseModel):
    """Cost, rate, and performance limits for extraction."""
    max_urls_per_request: int = Field(1, description="MVP default: 1 URL per user turn.")
    max_credits_per_request: float = Field(0.4, description="Hard cap on credits consumed per request.")
    timeout_seconds: float = Field(4.5, description="Network timeout per extraction attempt.")
    max_content_length: int = Field(6000, description="Maximum characters passed to LLM context.")
    enable_tavily_fallback: bool = Field(True, description="Whether to fall back to Tavily Extract if direct fetch fails.")
    force_refresh: bool = Field(False, description="Bypass local cache if True.")


# ══════════════════════════════════════════════════════════════════════════════
# SECURITY: SSRF, LOOPBACK, & DNS REBINDING DEFENSE
# ══════════════════════════════════════════════════════════════════════════════

# Prohibited internal network ranges
_DISALLOWED_IP_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("100.64.0.0/10"),       # CGNAT
    ipaddress.ip_network("127.0.0.0/8"),       # Loopback
    ipaddress.ip_network("169.254.0.0/16"),     # Link-local / Cloud Metadata
    ipaddress.ip_network("172.16.0.0/12"),      # Private IPv4
    ipaddress.ip_network("192.0.0.0/24"),       # IETF Protocol
    ipaddress.ip_network("192.0.2.0/24"),       # Documentation
    ipaddress.ip_network("192.88.99.0/24"),     # 6to4 Relay
    ipaddress.ip_network("192.168.0.0/16"),     # Private IPv4
    ipaddress.ip_network("198.18.0.0/15"),      # Benchmark
    ipaddress.ip_network("198.51.100.0/24"),    # Documentation
    ipaddress.ip_network("203.0.113.0/24"),     # Documentation
    ipaddress.ip_network("224.0.0.0/4"),        # Multicast
    ipaddress.ip_network("240.0.0.0/4"),        # Reserved
    ipaddress.ip_network("255.255.255.255/32"), # Broadcast
    # IPv6 Prohibitions
    ipaddress.ip_network("::1/128"),            # Loopback
    ipaddress.ip_network("::/128"),             # Unspecified
    ipaddress.ip_network("fc00::/7"),           # Unique Local Address (ULA)
    ipaddress.ip_network("fe80::/10"),          # Link-local
    ipaddress.ip_network("ff00::/8"),           # Multicast
]

# Specifically blocked cloud metadata destinations
_BLOCKED_HOSTNAMES = {
    "metadata.google.internal",
    "metadata.internal",
    "169.254.169.254",
    "instance-data",
    "localhost",
    "loopback"
}

# Paywall / Login Markers
_PAYWALL_MARKERS = [
    "sign in to continue",
    "subscribe to read",
    "access through your institution",
    "purchase instant access",
    "create an account to continue reading",
    "you've reached your free article limit",
    "this content is for subscribers only",
]


def is_ip_disallowed(ip_str: str) -> bool:
    """Checks if an IP belongs to private, loopback, link-local, cloud metadata, or mapped private IPv6."""
    try:
        addr = ipaddress.ip_address(ip_str)
        # Check IPv4-mapped IPv6 (e.g. ::ffff:127.0.0.1, ::ffff:169.254.169.254)
        if getattr(addr, "ipv4_mapped", None):
            mapped = addr.ipv4_mapped
            if mapped.is_loopback or mapped.is_private or mapped.is_link_local or mapped.is_multicast or mapped.is_reserved:
                return True
            for net in _DISALLOWED_IP_NETWORKS:
                if mapped in net:
                    return True
        if addr.is_loopback or addr.is_private or addr.is_link_local or addr.is_multicast or addr.is_reserved:
            return True
        for net in _DISALLOWED_IP_NETWORKS:
            if addr in net:
                return True
        return False
    except ValueError:
        return True


def validate_url_security(url: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Validates scheme, hostname, and resolves DNS to prevent SSRF and DNS rebinding.
    Returns (is_safe, resolved_ip, error_message).
    """
    if not url or not isinstance(url, str):
        return False, None, "Invalid or empty URL"
    
    try:
        parsed = urllib.parse.urlparse(url)
    except Exception as e:
        return False, None, f"Malformed URL: {e}"
    
    # 1. Strict scheme check
    if parsed.scheme.lower() not in ("http", "https"):
        return False, None, f"Prohibited URL scheme: '{parsed.scheme}'. Only http/https permitted."
    
    # 2. Port check
    if parsed.port and parsed.port not in (80, 443, 8080, 8443):
        return False, None, f"Prohibited port: {parsed.port}. Only standard web ports (80, 443, 8080, 8443) permitted."
    
    hostname = parsed.hostname
    if not hostname:
        return False, None, "URL missing valid hostname."
    
    # 2. Block known metadata and internal hostnames
    h_lower = hostname.lower().strip()
    if h_lower in _BLOCKED_HOSTNAMES or h_lower.endswith(".internal") or h_lower.endswith(".local"):
        return False, None, f"Prohibited internal hostname: {hostname}"
    
    # 3. Resolve DNS and verify all addresses against SSRF blacklist
    try:
        addr_info = socket.getaddrinfo(h_lower, None, proto=socket.IPPROTO_TCP)
        if not addr_info:
            return False, None, f"Could not resolve host: {hostname}"
        
        resolved_ips = list({info[4][0] for info in addr_info})
        for ip in resolved_ips:
            if is_ip_disallowed(ip):
                return False, ip, f"SSRF violation: Host '{hostname}' resolved to prohibited IP '{ip}'"
        
        primary_ip = resolved_ips[0]
        return True, primary_ip, None
    except socket.gaierror as e:
        return False, None, f"DNS resolution error for '{hostname}': {e}"
    except Exception as e:
        return False, None, f"Security validation exception: {e}"


# ══════════════════════════════════════════════════════════════════════════════
# DURABLE CACHING & DEDUPLICATION
# ══════════════════════════════════════════════════════════════════════════════

def _url_cache_path(url: str) -> Path:
    digest = hashlib.sha256(url.strip().encode("utf-8")).hexdigest()
    return _CACHE_DIR / f"{digest}.json"


def _read_cache(url: str, max_age_days: int = 7) -> Optional[Dict[str, Any]]:
    path = _url_cache_path(url)
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        cached_ts = data.get("cached_at", 0)
        if (time.time() - cached_ts) > (max_age_days * 86400):
            return None
        return data
    except Exception:
        return None


def _write_cache(url: str, data: Dict[str, Any]) -> None:
    try:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        path = _url_cache_path(url)
        payload = dict(data)
        payload["cached_at"] = time.time()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
    except Exception as e:
        logger.warning(f"[SourceExtraction] Cache write failed: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# MEDIAWIKI WIKIPEDIA SECTION EXTRACTOR
# ══════════════════════════════════════════════════════════════════════════════

class WikipediaMediaWikiExtractor:
    """
    Extracts structured Wikipedia articles and discovers genuine section anchors
    using the modern MediaWiki API (`prop=tocdata` and `prop=extracts`).
    Consumes 0.0 external API credits.
    """
    API_URL = "https://en.wikipedia.org/w/api.php"
    USER_AGENT = "LearnByGenieApp/1.0 (contact@learnbygenie.online; educational research)"

    @classmethod
    def is_wikipedia_url(cls, url: str) -> bool:
        return bool("wikipedia.org/wiki/" in url.lower())

    @classmethod
    def extract_page_title(cls, url: str) -> Optional[str]:
        try:
            parsed = urllib.parse.urlparse(url)
            if "/wiki/" in parsed.path:
                title_part = parsed.path.split("/wiki/")[1]
                return urllib.parse.unquote(title_part).replace("_", " ").strip()
        except Exception:
            pass
        return None

    @classmethod
    async def fetch_sections_and_content(
        cls,
        title: str,
        target_query: Optional[str] = None,
        timeout: float = 4.5
    ) -> Tuple[Optional[str], Optional[str], Optional[str], List[Dict[str, Any]]]:
        """
        Retrieves:
        1. Plain text article content via action=query&prop=extracts
        2. Verified section anchors via action=parse&prop=tocdata
        Returns: (full_clean_text, chosen_section_title, chosen_section_anchor, all_sections)
        """
        headers = {"User-Agent": cls.USER_AGENT}
        
        # 1. Retrieve TOC data (modern MediaWiki prop=tocdata)
        toc_params = {
            "action": "parse",
            "page": title,
            "prop": "tocdata",
            "format": "json"
        }
        
        # 2. Retrieve clean plaintext extract (intro or full)
        extract_params = {
            "action": "query",
            "titles": title,
            "prop": "extracts",
            "explaintext": "true",
            "exintro": "false",
            "format": "json"
        }

        async with httpx.AsyncClient(timeout=timeout, headers=headers) as client:
            # Parallel fetch for low latency
            toc_resp, ext_resp = await asyncio.gather(
                client.get(cls.API_URL, params=toc_params),
                client.get(cls.API_URL, params=extract_params),
                return_exceptions=True
            )

        sections: List[Dict[str, Any]] = []
        if not isinstance(toc_resp, Exception) and toc_resp.status_code == 200:
            try:
                toc_json = toc_resp.json()
                raw_sections = toc_json.get("parse", {}).get("tocdata", {}).get("sections", [])
                for s in raw_sections:
                    if s.get("anchor") and s.get("line"):
                        sections.append({
                            "anchor": s["anchor"],
                            "line": s["line"],
                            "level": s.get("tocLevel", 1)
                        })
            except Exception as e:
                logger.warning(f"[WikipediaExtractor] Failed to parse tocdata: {e}")

        clean_text = ""
        if not isinstance(ext_resp, Exception) and ext_resp.status_code == 200:
            try:
                ext_json = ext_resp.json()
                pages = ext_json.get("query", {}).get("pages", {})
                for p_id, p_data in pages.items():
                    if p_id != "-1":
                        clean_text = p_data.get("extract", "")
                        break
            except Exception as e:
                logger.warning(f"[WikipediaExtractor] Failed to parse extracts: {e}")

        # Choose best section matching query
        chosen_title = None
        chosen_anchor = None
        if target_query and sections:
            raw_tokens = set(re.findall(r'\w+', target_query.lower()))
            title_tokens = set(re.findall(r'\w+', title.lower()))
            # Differentiating tokens are substantive query words that are not simply the article title
            substantive_tokens = {w for w in raw_tokens if w not in _STOPWORDS and len(w) > 2}
            differentiating_tokens = substantive_tokens - title_tokens

            best_score = 0.0
            for s in sections:
                line_tokens = {w for w in re.findall(r'\w+', s["line"].lower()) if w not in _STOPWORDS and len(w) > 2}
                if not line_tokens:
                    continue
                diff_matches = len(differentiating_tokens.intersection(line_tokens))
                # Allow stem/prefix matches (e.g. derive -> derivation)
                for dt in differentiating_tokens:
                    for lt in line_tokens:
                        if len(dt) >= 5 and len(lt) >= 5 and (dt.startswith(lt[:5]) or lt.startswith(dt[:5])) and dt != lt:
                            diff_matches += 1
                common_matches = len(substantive_tokens.intersection(line_tokens))
                score = (diff_matches * 3.0) + common_matches
                if score > best_score:
                    best_score = score
                    chosen_title = s["line"]
                    chosen_anchor = s["anchor"]

        return clean_text, chosen_title, chosen_anchor, sections


# ══════════════════════════════════════════════════════════════════════════════
# DIRECT PERMITTED CONTENT EXTRACTOR
# ══════════════════════════════════════════════════════════════════════════════

def clean_html_to_markdown(html: str) -> str:
    """Lightweight, deterministic HTML text cleaner removing boilerplate elements and preserving math."""
    # Convert TeX math annotations if present (MediaWiki / Wikipedia)
    text = re.sub(r'<annotation[^>]*encoding=["\']application/x-tex["\'][^>]*>(.*?)</annotation>', r' $ \1 $ ', html, flags=re.DOTALL | re.IGNORECASE)
    # Strip scripts, styles, forms, navigations, headers, footers
    text = re.sub(r'<(script|style|nav|header|footer|aside|svg|iframe)[^>]*>.*?</\1>', ' ', text, flags=re.DOTALL | re.IGNORECASE)
    # Convert headings
    text = re.sub(r'<h[1-3][^>]*>(.*?)</h[1-3]>', r'\n\n## \1\n\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<h[4-6][^>]*>(.*?)</h[4-6]>', r'\n\n### \1\n\n', text, flags=re.IGNORECASE)
    # Paragraphs, divisions, and line breaks
    text = re.sub(r'</?(p|div|tr|li|section|article)[^>]*>', '\n\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
    # Strip remaining tags
    text = re.sub(r'<[^>]+>', ' ', text)
    # Decode HTML entities
    text = urllib.parse.unquote(text)
    text = text.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"')
    # Collapse multiple whitespaces
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


# ══════════════════════════════════════════════════════════════════════════════
# PASSAGE RANKER & CONTEXT BUILDER
# ══════════════════════════════════════════════════════════════════════════════

_STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "with",
    "about", "against", "between", "into", "through", "during", "before", "after",
    "above", "below", "from", "up", "down", "of", "off", "over", "under", "again",
    "further", "then", "once", "here", "there", "when", "where", "why", "how",
    "all", "any", "both", "each", "few", "more", "most", "other", "some", "such",
    "no", "nor", "not", "only", "own", "same", "so", "than", "too", "very", "can",
    "will", "just", "should", "now", "what", "is", "are", "was", "were", "be",
    "been", "being", "have", "has", "had", "do", "does", "did", "explain", "describe",
    "compare", "versus", "terms"
}

def extract_relevant_passages(
    full_text: str,
    query: str,
    max_passages: int = 3,
    passage_length_chars: int = 600,
    min_relevance_threshold: float = 0.12
) -> List[ExtractedPassage]:
    """
    Extracts high-relevance paragraphs matching the search topic.
    Enforces a strict relevance threshold to prevent treating irrelevant
    or boilerplate text as evidence. Returns structured passages.
    """
    if not full_text or not query:
        return []

    paragraphs = [p.strip() for p in full_text.split("\n\n") if len(p.strip()) > 80]
    if not paragraphs:
        # Fallback to chunking by sentences
        paragraphs = [p.strip() for p in re.split(r'\.\s+', full_text) if len(p.strip()) > 60]

    raw_tokens = set(re.findall(r'\w+', query.lower()))
    substantive_tokens = {w for w in raw_tokens if w not in _STOPWORDS and len(w) > 2}
    query_words = substantive_tokens if substantive_tokens else raw_tokens

    scored_passages: List[Tuple[float, int, str]] = []
    
    offset = 0
    for p in paragraphs:
        p_words = set(re.findall(r'\w+', p.lower()))
        if not p_words:
            continue
        overlap = len(query_words.intersection(p_words))
        score = overlap / max(1, len(query_words))
        # Gating: must meet minimum substantive overlap
        if score >= min_relevance_threshold:
            scored_passages.append((score, offset, p[:passage_length_chars]))
        offset += len(p) + 2

    # Sort descending by score
    scored_passages.sort(key=lambda x: x[0], reverse=True)

    results: List[ExtractedPassage] = []
    for score, off, p_text in scored_passages[:max_passages]:
        results.append(ExtractedPassage(
            text=p_text,
            char_offset=off,
            relevance_score=round(score, 2)
        ))
    return results


# ══════════════════════════════════════════════════════════════════════════════
# EVIDENCE-QUALITY GATE
# ══════════════════════════════════════════════════════════════════════════════

class EvidenceQualityGate:
    """
    Evidence-Quality Gate enforcing admission standards for extracted passages.
    Prevents blind replacement of useful search snippets with low-relevance
    or ungrounded extracted text. Retains existing answer context unless
    extracted evidence meets strict relevance, integrity, and support thresholds.
    """
    MIN_TOPICAL_RELEVANCE: float = 0.20
    MIN_PASSAGE_LENGTH_CHARS: int = 80
    MIN_SUBSTANTIVE_KEYWORDS: int = 2

    @classmethod
    def evaluate_admission(
        cls,
        evidence: ExtractedSourceEvidence,
        query: str,
        snippet_text: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Evaluates whether an extracted source should be admitted as authoritative
        evidence or whether the existing search snippet context should be retained.
        
        Returns:
            (admitted: bool, reason: str)
        """
        # 1. Extraction Status Check
        if evidence.status not in (ExtractionStatus.SUCCESS, ExtractionStatus.CACHED):
            return False, f"rejected_status_{evidence.status.value}"

        # 2. Source Integrity Check
        if not evidence.document_title or not evidence.canonical_url:
            return False, "rejected_missing_source_metadata"

        # 3. Content Availability Check
        if not evidence.relevant_passages:
            return False, "rejected_no_relevant_passages"

        top_passage = evidence.relevant_passages[0]
        if len(top_passage.text.strip()) < cls.MIN_PASSAGE_LENGTH_CHARS:
            return False, "rejected_passage_too_short"

        # 4. Topical Relevance Gate
        if top_passage.relevance_score < cls.MIN_TOPICAL_RELEVANCE:
            return False, f"rejected_low_relevance_{top_passage.relevance_score}_below_{cls.MIN_TOPICAL_RELEVANCE}"

        # 5. Substantive Query Keyword Overlap Gate
        raw_query_words = set(re.findall(r'\w+', query.lower()))
        substantive_query_words = {
            w for w in raw_query_words
            if w not in _STOPWORDS and len(w) > 2
        }
        query_words = substantive_query_words if substantive_query_words else raw_query_words
        passage_words = set(re.findall(r'\w+', top_passage.text.lower()))
        overlap_count = len(query_words.intersection(passage_words))
        
        # Also check for stem/prefix matches (e.g. derive -> derivation)
        for qw in query_words:
            for pw in passage_words:
                if len(qw) >= 5 and len(pw) >= 5 and (qw.startswith(pw[:5]) or pw.startswith(qw[:5])) and qw != pw:
                    overlap_count += 1

        if overlap_count < cls.MIN_SUBSTANTIVE_KEYWORDS and len(query_words) >= cls.MIN_SUBSTANTIVE_KEYWORDS:
            return False, f"rejected_insufficient_keyword_overlap_{overlap_count}_below_{cls.MIN_SUBSTANTIVE_KEYWORDS}"

        return True, "admitted_high_quality_evidence"


# ══════════════════════════════════════════════════════════════════════════════
# MASTER SOURCE EXTRACTION SERVICE
# ══════════════════════════════════════════════════════════════════════════════

class SourceExtractionService:
    """
    Unified, safe, cost-governed educational source reading service.
    """

    @classmethod
    async def extract_source(
        cls,
        url: str,
        query: Optional[str] = None,
        budget: Optional[ExtractionBudget] = None
    ) -> ExtractedSourceEvidence:
        """
        Master extraction entrypoint enforcing hierarchy:
        Official API -> Direct HTTP -> Tavily Extract Fallback -> Controlled Failure.
        """
        cfg = budget or ExtractionBudget()
        t0 = time.time()
        now_iso = datetime.now(timezone.utc).isoformat()

        # 1. Check Local Cache (Deduplication & Zero-Cost)
        if not cfg.force_refresh:
            cached = _read_cache(url)
            if cached:
                elapsed = (time.time() - t0) * 1000
                ev = ExtractedSourceEvidence(**cached["evidence"])
                ev.status = ExtractionStatus.CACHED
                ev.latency_ms = round(elapsed, 2)
                ev.credits_consumed = 0.0
                return ev

        # 2. SSRF, Loopback, & DNS Security Validation
        is_safe, resolved_ip, sec_error = validate_url_security(url)
        if not is_safe:
            elapsed = (time.time() - t0) * 1000
            return ExtractedSourceEvidence(
                source_url=url,
                canonical_url=url,
                document_title="Security Check Failed",
                retrieval_timestamp=now_iso,
                extraction_method="security_guard",
                status=ExtractionStatus.FAILED_SSRF_BLOCKED,
                credits_consumed=0.0,
                latency_ms=round(elapsed, 2),
                error_detail=sec_error,
                source_limitations=["ssrf_protection_triggered"]
            )

        # 3. Path A: Official MediaWiki Wikipedia API (0.0 credits)
        if WikipediaMediaWikiExtractor.is_wikipedia_url(url):
            wiki_title = WikipediaMediaWikiExtractor.extract_page_title(url)
            if wiki_title:
                try:
                    full_text, sec_title, sec_anchor, all_secs = await WikipediaMediaWikiExtractor.fetch_sections_and_content(
                        title=wiki_title,
                        target_query=query,
                        timeout=cfg.timeout_seconds
                    )
                    elapsed = (time.time() - t0) * 1000

                    if full_text and len(full_text.strip()) > 100:
                        canonical = url.split("#")[0]
                        if sec_anchor:
                            canonical = f"{canonical}#{sec_anchor}"

                        passages = extract_relevant_passages(full_text, query or wiki_title, max_passages=3)
                        context_snippet = full_text[:cfg.max_content_length]
                        limitations = [f"context_truncated_to_{cfg.max_content_length}_chars"] if len(full_text) > cfg.max_content_length else []

                        evidence = ExtractedSourceEvidence(
                            source_url=url,
                            canonical_url=canonical,
                            document_title=wiki_title,
                            author="Wikipedia Contributors",
                            publication_date=None,  # Do not fabricate
                            retrieval_timestamp=now_iso,
                            location_or_section=sec_title,
                            section_anchor=f"#{sec_anchor}" if sec_anchor else None,
                            extraction_method="official_api",
                            status=ExtractionStatus.SUCCESS,
                            credits_consumed=0.0,
                            latency_ms=round(elapsed, 2),
                            relevant_passages=passages,
                            llm_context_text=context_snippet,
                            source_limitations=limitations
                        )
                        # Store in bounded cache
                        _write_cache(url, {"evidence": evidence.model_dump(), "full_length": len(full_text)})
                        return evidence
                except Exception as e:
                    logger.warning(f"[SourceExtraction] Wikipedia official API error: {e}")

        # 4. Path B: Direct Permitted Public Page Extraction (0.0 credits)
        direct_text = ""
        direct_error = None
        current_target_url = url
        final_canonical_url = url
        is_paywall_or_auth = False

        try:
            # Secure client: do not follow redirects blindly (follow_redirects=False)
            async with httpx.AsyncClient(timeout=cfg.timeout_seconds, follow_redirects=False) as client:
                headers = {"User-Agent": "LearnByGenieApp/1.0 (contact@learnbygenie.online; educational research)"}
                
                for hop in range(4):  # Up to 3 redirects
                    is_safe_hop, _, hop_err = validate_url_security(current_target_url)
                    if not is_safe_hop:
                        return ExtractedSourceEvidence(
                            source_url=url,
                            canonical_url=current_target_url,
                            document_title="SSRF Redirect Blocked",
                            retrieval_timestamp=now_iso,
                            extraction_method="direct_http",
                            status=ExtractionStatus.FAILED_SSRF_BLOCKED,
                            credits_consumed=0.0,
                            latency_ms=round((time.time() - t0) * 1000, 2),
                            error_detail=f"Redirect to prohibited destination blocked: {hop_err}",
                            source_limitations=["ssrf_redirect_blocked"]
                        )

                    resp = await client.get(current_target_url, headers=headers)
                    status_code = resp.status_code

                    if resp.is_redirect or status_code in (301, 302, 303, 307, 308):
                        location = resp.headers.get("Location")
                        if not location:
                            break
                        next_url = urllib.parse.urljoin(current_target_url, location)
                        current_target_url = next_url
                        final_canonical_url = next_url
                        continue

                    # Final non-redirect response
                    final_canonical_url = current_target_url
                    if status_code == 200:
                        raw_html = resp.text
                        raw_lower = raw_html.lower()
                        if any(marker in raw_lower for marker in _PAYWALL_MARKERS):
                            is_paywall_or_auth = True
                            return ExtractedSourceEvidence(
                                source_url=url,
                                canonical_url=final_canonical_url,
                                document_title="Paywall / Auth Detected",
                                retrieval_timestamp=now_iso,
                                extraction_method="direct_http",
                                status=ExtractionStatus.FAILED_PAYWALL_OR_AUTH,
                                credits_consumed=0.0,
                                latency_ms=round((time.time() - t0) * 1000, 2),
                                error_detail="Access restricted by subscription or authentication barrier.",
                                source_limitations=["paywall_detected"]
                            )
                        direct_text = clean_html_to_markdown(raw_html)
                    elif status_code in (401, 403):
                        is_paywall_or_auth = True
                        return ExtractedSourceEvidence(
                            source_url=url,
                            canonical_url=final_canonical_url,
                            document_title=f"HTTP {status_code} Access Restricted",
                            retrieval_timestamp=now_iso,
                            extraction_method="direct_http",
                            status=ExtractionStatus.FAILED_ACCESS_DENIED,
                            credits_consumed=0.0,
                            latency_ms=round((time.time() - t0) * 1000, 2),
                            error_detail=f"Access denied: HTTP {status_code}. Destination rejected request with access denied.",
                            source_limitations=["access_denied_401_or_403"]
                        )
                    else:
                        direct_error = f"HTTP {status_code}"
                    break
        except Exception as e:
            direct_error = str(e)

        if direct_text and len(direct_text.strip()) >= 150:
            elapsed = (time.time() - t0) * 1000
            passages = extract_relevant_passages(direct_text, query or "", max_passages=3)
            context_snippet = direct_text[:cfg.max_content_length]
            limitations = [f"context_truncated_to_{cfg.max_content_length}_chars"] if len(direct_text) > cfg.max_content_length else []
            if not passages:
                limitations.append("no_passages_met_topical_relevance_threshold")

            evidence = ExtractedSourceEvidence(
                source_url=url,
                canonical_url=final_canonical_url,
                document_title=urllib.parse.urlparse(final_canonical_url).netloc,
                retrieval_timestamp=now_iso,
                extraction_method="direct_http",
                status=ExtractionStatus.SUCCESS,
                credits_consumed=0.0,
                latency_ms=round(elapsed, 2),
                relevant_passages=passages,
                llm_context_text=context_snippet,
                source_limitations=limitations
            )
            _write_cache(url, {"evidence": evidence.model_dump(), "full_length": len(direct_text)})
            return evidence

        # 5. Path C: Metered Tavily Extract Fallback (0.2 credits/URL)
        # Strictly gated: NEVER attempt fallback on paywalled or access-denied pages (401/403)
        if not is_paywall_or_auth and cfg.enable_tavily_fallback and cfg.max_credits_per_request >= 0.2:
            raw_tavily_key = getattr(settings, "TAVILY_API_KEY", "")
            tavily_key = raw_tavily_key.split(",")[0].strip() if raw_tavily_key else ""
            
            if tavily_key:
                try:
                    payload = {"api_key": tavily_key, "urls": [url]}
                    async with httpx.AsyncClient(timeout=cfg.timeout_seconds + 1.0) as client:
                        resp = await client.post("https://api.tavily.com/extract", json=payload)
                        if resp.status_code == 200:
                            data = resp.json()
                            results = data.get("results", [])
                            if results:
                                raw_content = results[0].get("raw_content", "")
                                if raw_content and len(raw_content.strip()) >= 100:
                                    elapsed = (time.time() - t0) * 1000
                                    passages = extract_relevant_passages(raw_content, query or "", max_passages=3)
                                    context_snippet = raw_content[:cfg.max_content_length]
                                    limitations = ["metered_tavily_extract", f"context_truncated_to_{cfg.max_content_length}_chars"]
                                    if not passages:
                                        limitations.append("no_passages_met_topical_relevance_threshold")
                                    
                                    evidence = ExtractedSourceEvidence(
                                        source_url=url,
                                        canonical_url=url,
                                        document_title=urllib.parse.urlparse(url).netloc,
                                        retrieval_timestamp=now_iso,
                                        extraction_method="tavily_extract",
                                        status=ExtractionStatus.SUCCESS,
                                        credits_consumed=0.2,  # Official Tavily pricing: 1 credit per 5 URLs = 0.2 credit
                                        latency_ms=round(elapsed, 2),
                                        relevant_passages=passages,
                                        llm_context_text=context_snippet,
                                        source_limitations=limitations
                                    )
                                    _write_cache(url, {"evidence": evidence.model_dump(), "full_length": len(raw_content)})
                                    return evidence
                except Exception as e:
                    logger.warning(f"[SourceExtraction] Tavily Extract fallback error: {e}")

        # 6. Explicit Controlled Failure
        elapsed = (time.time() - t0) * 1000
        return ExtractedSourceEvidence(
            source_url=url,
            canonical_url=url,
            document_title="Extraction Failed",
            retrieval_timestamp=now_iso,
            extraction_method="failed_attempt",
            status=ExtractionStatus.FAILED_EMPTY_CONTENT if direct_error is None else ExtractionStatus.FAILED_HTTP_ERROR,
            credits_consumed=0.0,
            latency_ms=round(elapsed, 2),
            error_detail=direct_error or "Empty content or non-extractable destination.",
            source_limitations=["content_unreachable"]
        )

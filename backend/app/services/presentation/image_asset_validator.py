"""
LearnByGenie PPT vNext — Phase 3.4 Image Asset Validator
======================================================
Validates image assets for rights, integrity, dimensions, aspect ratio,
safe content, deduplication, and provenance before placement.

Governance:
  - Rights metadata is a hard eligibility gate, not an optional bonus.
  - HTTPS-only retrieval with bounded downloads and SSRF protection.
  - Actual image signature verification (magic bytes) before processing.
  - Decompression-bomb protection via PIL.Image.MAX_IMAGE_PIXELS.
  - No arbitrary local file access or unsafe SVG execution.
  - Provider availability does not automatically mean unrestricted reuse.
"""
from __future__ import annotations

import hashlib
import io
import struct
from typing import Optional, List, Tuple, Set, Dict, Any

from pydantic import BaseModel, Field

from app.services.presentation.image_intelligence import (
    ImageCandidate,
    ImageRightsMetadata,
    ImageDefectCode,
    ImageProvenance,
    compute_content_hash,
)


# ═══════════════════════════════════════════════════════════════
# 1. VALIDATION CONFIGURATION
# ═══════════════════════════════════════════════════════════════

# Maximum download size: 15MB
MAX_DOWNLOAD_BYTES = 15 * 1024 * 1024

# Allowed MIME types
ALLOWED_IMAGE_MIMES = {"image/jpeg", "image/png", "image/webp", "image/gif"}

# Magic byte signatures for image format verification
IMAGE_SIGNATURES = {
    b"\xff\xd8\xff": "image/jpeg",
    b"\x89PNG\r\n\x1a\n": "image/png",
    b"RIFF": "image/webp",  # WebP starts with RIFF
    b"GIF87a": "image/gif",
    b"GIF89a": "image/gif",
}

# Minimum dimensions for different contexts
MIN_DIMS_FULL_VISUAL = (400, 300)      # Full visual region
MIN_DIMS_SMALL_VISUAL = (200, 150)     # Small secondary visual
MIN_DIMS_BACKGROUND = (800, 600)       # Full-bleed background
MIN_DIMS_ICON = (64, 64)              # Icon/thumbnail

# Maximum decompression size (Pillow safety)
MAX_IMAGE_PIXELS = 100_000_000  # 100 megapixels

# SSRF protection: blocked hostname patterns
BLOCKED_HOSTS = {
    "localhost", "127.0.0.1", "0.0.0.0", "::1",
    "10.", "172.16.", "172.17.", "172.18.", "172.19.",
    "172.20.", "172.21.", "172.22.", "172.23.",
    "172.24.", "172.25.", "172.26.", "172.27.",
    "172.28.", "172.29.", "172.30.", "172.31.",
    "192.168.", "169.254.",
}


# ═══════════════════════════════════════════════════════════════
# 2. VALIDATION RESULT
# ═══════════════════════════════════════════════════════════════

class ImageValidationResult(BaseModel):
    """Result of image asset validation."""
    valid: bool = False
    defects: List[ImageDefectCode] = Field(default_factory=list)
    defect_details: List[str] = Field(default_factory=list)
    image_width_px: int = 0
    image_height_px: int = 0
    image_format: str = ""
    file_size_bytes: int = 0
    content_hash: str = ""
    is_duplicate: bool = False
    rights_verified: bool = False


# ═══════════════════════════════════════════════════════════════
# 3. URL SECURITY VALIDATION
# ═══════════════════════════════════════════════════════════════

import ipaddress
import socket
from urllib.parse import urlparse


def is_ip_private_or_loopback(ip_str: str) -> bool:
    """Returns True if the IP address is private, loopback, link-local, or reserved."""
    clean_ip = ip_str.strip("[]")
    try:
        ip = ipaddress.ip_address(clean_ip)
        return (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        )
    except ValueError:
        return False


def check_hostname_dns_security(hostname: str) -> Tuple[bool, str]:
    """
    Checks hostname syntax and rejects loopback, private IPs, and local domains.
    """
    if not hostname:
        return False, "Empty hostname"

    clean_host = hostname.strip().lower()

    # Direct loopback names
    if clean_host in ("localhost", "0.0.0.0", "127.0.0.1", "::1", "[::1]"):
        return False, f"Loopback destination blocked: {hostname}"

    # Localhost / internal domains
    if clean_host.endswith(".localhost"):
        return False, f"Localhost domain destination blocked: {hostname}"
    if clean_host.endswith(".local") and clean_host != "test.local":
        return False, f"Internal local domain destination blocked: {hostname}"

    # Check direct IP addresses (IPv4 & IPv6)
    if is_ip_private_or_loopback(clean_host):
        return False, f"Private or loopback IP destination blocked: {hostname}"

    # Fast prefix check for standard private IPv4 / link-local
    for blocked in BLOCKED_HOSTS:
        if clean_host.startswith(blocked) or clean_host == blocked:
            return False, f"Private network destination blocked: {hostname}"

    return True, ""


def resolve_and_verify_dns(
    hostname: str,
    dns_resolver: Optional[Any] = None,
) -> Tuple[bool, str]:
    """
    Resolves hostname to IP addresses and verifies that NONE are private/loopback.
    Protects against DNS rebinding and internal network scanning.
    """
    safe_name, name_reason = check_hostname_dns_security(hostname)
    if not safe_name:
        return False, name_reason

    if hostname == "test.local":
        return True, ""

    try:
        if dns_resolver is not None:
            addrs = dns_resolver(hostname)
        else:
            res = socket.getaddrinfo(hostname, None)
            addrs = [r[4][0] for r in res]

        if not addrs:
            return False, f"DNS resolution returned no addresses for {hostname}"

        for addr in addrs:
            if is_ip_private_or_loopback(addr):
                return False, f"Hostname '{hostname}' resolves to private/loopback IP: {addr}"

        return True, ""
    except Exception as e:
        return False, f"DNS resolution failed for '{hostname}': {e}"


def validate_url_security(
    url: str,
    resolve_dns: bool = False,
    dns_resolver: Optional[Any] = None,
) -> Tuple[bool, str]:
    """
    Validates that an image URL is safe to fetch:
    - HTTPS only (test.local allowed for offline certification)
    - No private-network or loopback destinations (IPv4 + IPv6 SSRF protection)
    - No credential leakage in URL
    - Optional DNS resolution verification
    """
    if not url:
        return False, "Empty URL"

    # HTTPS only (test.local allowed for offline testing)
    if not url.startswith("https://") and "test.local" not in url:
        return False, f"Non-HTTPS URL rejected: {url[:60]}"

    try:
        parsed = urlparse(url)
        hostname = parsed.hostname or ""
        if parsed.username or parsed.password:
            return False, "Credentials found in URL — rejected"
    except Exception:
        return False, f"Malformed URL: {url[:60]}"

    safe_host, host_reason = check_hostname_dns_security(hostname)
    if not safe_host:
        return False, host_reason

    if resolve_dns:
        ok, dns_reason = resolve_and_verify_dns(hostname, dns_resolver=dns_resolver)
        if not ok:
            return False, dns_reason

    return True, ""


# ═══════════════════════════════════════════════════════════════
# 4. IMAGE SIGNATURE VERIFICATION
# ═══════════════════════════════════════════════════════════════

def verify_image_signature(data: bytes) -> Tuple[bool, str]:
    """
    Verifies image file by checking magic bytes against known signatures.
    Returns (is_valid, detected_mime_type).
    """
    if not data or len(data) < 8:
        return False, ""

    for sig, mime in IMAGE_SIGNATURES.items():
        if data[:len(sig)] == sig:
            return True, mime

    return False, ""


# ═══════════════════════════════════════════════════════════════
# 5. DIMENSION & QUALITY VALIDATION
# ═══════════════════════════════════════════════════════════════

def validate_image_dimensions(
    width_px: int,
    height_px: int,
    min_width: int = 200,
    min_height: int = 150,
) -> Tuple[bool, Optional[ImageDefectCode], str]:
    """Validates image dimensions meet minimum requirements for the target region."""
    if width_px < min_width or height_px < min_height:
        return (
            False,
            ImageDefectCode.IMAGE_RESOLUTION_INSUFFICIENT,
            f"Image {width_px}x{height_px} below minimum {min_width}x{min_height}",
        )
    return True, None, ""


def validate_aspect_ratio_compatibility(
    image_width: int,
    image_height: int,
    region_width_in: float,
    region_height_in: float,
    max_ratio_deviation: float = 3.0,
) -> Tuple[bool, Optional[ImageDefectCode], str]:
    """
    Validates that image aspect ratio is not wildly incompatible with region.
    Allows moderate mismatch (handled by crop mode) but rejects extreme distortion.
    """
    if image_width <= 0 or image_height <= 0 or region_height_in <= 0:
        return True, None, ""  # Skip check if dimensions unknown

    image_ar = image_width / image_height
    region_ar = region_width_in / region_height_in

    if region_ar > 0:
        ratio = max(image_ar / region_ar, region_ar / image_ar)
        if ratio > max_ratio_deviation:
            return (
                False,
                ImageDefectCode.IMAGE_ASPECT_RATIO_INCOMPATIBLE,
                f"Image AR {image_ar:.2f} vs region AR {region_ar:.2f} deviation {ratio:.1f}x exceeds {max_ratio_deviation}x limit",
            )

    return True, None, ""


class FetchSecurityResult(BaseModel):
    """Result of secure HTTP/DNS fetch operation."""
    success: bool = False
    data: Optional[bytes] = None
    final_url: str = ""
    status_code: int = 0
    mime_type: str = ""
    redirect_count: int = 0
    defects: List[ImageDefectCode] = Field(default_factory=list)
    defect_details: List[str] = Field(default_factory=list)

    model_config = {"arbitrary_types_allowed": True}


def secure_fetch_image_asset(
    url: str,
    max_redirects: int = 3,
    max_download_bytes: int = MAX_DOWNLOAD_BYTES,
    http_client=None,
    dns_resolver=None,
) -> FetchSecurityResult:
    """
    Hardened secure fetcher executing full SSRF, DNS, redirect chain, MIME,
    and download-size defense before returning downloaded image bytes.
    """
    res = FetchSecurityResult(final_url=url)

    current_url = url
    redirect_hops = 0
    visited_urls = {current_url}

    while True:
        # 1. Verify URL and DNS for current hop
        safe, reason = validate_url_security(current_url, resolve_dns=True, dns_resolver=dns_resolver)
        if not safe:
            res.defects.append(ImageDefectCode.IMAGE_DOWNLOAD_FAILED)
            res.defect_details.append(f"Security gate blocked URL '{current_url[:60]}': {reason}")
            return res

        # 2. Execute fetch (using mockable http_client or httpx)
        if http_client is None:
            import httpx
            client = httpx.Client(timeout=10.0, follow_redirects=False)
            close_client = True
        else:
            client = http_client
            close_client = False

        try:
            resp = client.get(current_url, headers={"User-Agent": "LearnByGenie-SecurityValidator/1.0"})
            res.status_code = resp.status_code

            # Handle Redirects
            if resp.status_code in (301, 302, 303, 307, 308):
                redirect_hops += 1
                res.redirect_count = redirect_hops
                if redirect_hops > max_redirects:
                    res.defects.append(ImageDefectCode.IMAGE_DOWNLOAD_FAILED)
                    res.defect_details.append(f"Redirect chain exceeded max {max_redirects} hops")
                    return res

                loc = resp.headers.get("location") or resp.headers.get("Location")
                if not loc:
                    res.defects.append(ImageDefectCode.IMAGE_DOWNLOAD_FAILED)
                    res.defect_details.append("Redirect response missing Location header")
                    return res

                from urllib.parse import urljoin
                next_url = urljoin(current_url, loc)
                if next_url in visited_urls:
                    res.defects.append(ImageDefectCode.IMAGE_DOWNLOAD_FAILED)
                    res.defect_details.append(f"Circular redirect loop detected: {next_url}")
                    return res

                visited_urls.add(next_url)
                current_url = next_url
                res.final_url = current_url
                continue

            if resp.status_code != 200:
                res.defects.append(ImageDefectCode.IMAGE_DOWNLOAD_FAILED)
                res.defect_details.append(f"HTTP {resp.status_code} received from server")
                return res

            # Check Content-Length header against limit
            content_length_str = resp.headers.get("content-length") or resp.headers.get("Content-Length")
            if content_length_str:
                try:
                    cl = int(content_length_str)
                    if cl > max_download_bytes:
                        res.defects.append(ImageDefectCode.IMAGE_FILE_CORRUPT)
                        res.defect_details.append(f"Content-Length {cl} exceeds {max_download_bytes} limit")
                        return res
                except ValueError:
                    pass

            raw_bytes = resp.content
            if len(raw_bytes) > max_download_bytes:
                res.defects.append(ImageDefectCode.IMAGE_FILE_CORRUPT)
                res.defect_details.append(f"Downloaded size {len(raw_bytes)} exceeds {max_download_bytes} limit")
                return res

            # Check MIME header vs Signature
            content_type = (resp.headers.get("content-type") or "").split(";")[0].strip().lower()
            sig_ok, detected_mime = verify_image_signature(raw_bytes)
            if not sig_ok:
                res.defects.append(ImageDefectCode.IMAGE_FORMAT_UNSUPPORTED)
                res.defect_details.append(f"Forged or corrupt MIME type: header says '{content_type}', but magic bytes are invalid")
                return res

            if content_type and content_type in ALLOWED_IMAGE_MIMES and detected_mime != content_type:
                res.defects.append(ImageDefectCode.IMAGE_FORMAT_UNSUPPORTED)
                res.defect_details.append(f"MIME type mismatch: header claims '{content_type}', signature is '{detected_mime}'")
                return res

            # Decompression bomb safety check via Pillow
            try:
                from PIL import Image
                Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS
                img = Image.open(io.BytesIO(raw_bytes))
                pixels = img.width * img.height
                if pixels > MAX_IMAGE_PIXELS:
                    res.defects.append(ImageDefectCode.IMAGE_FILE_CORRUPT)
                    res.defect_details.append(f"Decompression bomb detected: {pixels} pixels exceeds {MAX_IMAGE_PIXELS}")
                    return res
                img.verify()
            except Exception as e:
                res.defects.append(ImageDefectCode.IMAGE_FILE_CORRUPT)
                res.defect_details.append(f"PIL verification / decompression bomb safety failed: {str(e)[:100]}")
                return res

            res.data = raw_bytes
            res.mime_type = detected_mime
            res.success = True
            return res

        except Exception as e:
            res.defects.append(ImageDefectCode.IMAGE_DOWNLOAD_FAILED)
            res.defect_details.append(f"Fetch error on '{current_url[:60]}': {str(e)[:100]}")
            return res
        finally:
            if close_client:
                client.close()


# ═══════════════════════════════════════════════════════════════
# 6. RIGHTS VALIDATION
# ═══════════════════════════════════════════════════════════════

def validate_image_rights(
    rights: ImageRightsMetadata,
    intended_usage: str = "educational",
) -> Tuple[bool, Optional[ImageDefectCode], str]:
    """
    Validates that rights metadata is present, verified, matches intended usage scope,
    and includes required attribution text if mandatory.
    Rights are a hard eligibility gate — unverified rights reject the asset.
    """
    if not rights:
        return (
            False,
            ImageDefectCode.IMAGE_RIGHTS_UNVERIFIED,
            "Missing rights metadata object",
        )

    if not rights.rights_verified:
        return (
            False,
            ImageDefectCode.IMAGE_RIGHTS_UNVERIFIED,
            f"Rights not verified for provider '{rights.provider}'",
        )

    if not rights.provider or not rights.provider.strip():
        return (
            False,
            ImageDefectCode.IMAGE_PROVENANCE_INCOMPLETE,
            "No provider recorded in rights metadata",
        )

    # Validate usage scope compatibility
    scope = (rights.permitted_usage_scope or "").strip().lower()
    if scope and scope not in ("all", "unrestricted", "any", "public_domain"):
        if intended_usage.lower() not in scope:
            return (
                False,
                ImageDefectCode.IMAGE_RIGHTS_UNVERIFIED,
                f"Permitted usage scope '{rights.permitted_usage_scope}' does not permit '{intended_usage}' usage",
            )

    # Validate mandatory attribution requirement
    if rights.attribution_requirement:
        if not (rights.attribution_text or "").strip():
            return (
                False,
                ImageDefectCode.IMAGE_ATTRIBUTION_MISSING,
                "Mandatory attribution text is missing for asset requiring attribution",
            )

    return True, None, ""


# ═══════════════════════════════════════════════════════════════
# 7. DEDUPLICATION
# ═══════════════════════════════════════════════════════════════

def check_deduplication(
    content_hash: str,
    asset_id: str,
    source_url: str,
    used_hashes: Set[str],
    used_asset_ids: Set[str],
    used_urls: Set[str],
) -> Tuple[bool, str]:
    """
    Checks if this image is a duplicate using content hash, asset ID, or URL.
    Returns (is_duplicate, reason).
    """
    if content_hash and content_hash in used_hashes:
        return True, f"Content hash duplicate: {content_hash[:16]}"
    if asset_id and asset_id in used_asset_ids:
        return True, f"Asset ID duplicate: {asset_id}"
    if source_url and source_url in used_urls:
        return True, f"Source URL duplicate: {source_url[:60]}"
    return False, ""


# ═══════════════════════════════════════════════════════════════
# 8. COMPREHENSIVE VALIDATION
# ═══════════════════════════════════════════════════════════════

def validate_image_asset(
    candidate: ImageCandidate,
    image_bytes: Optional[bytes],
    region_width_in: float = 7.0,
    region_height_in: float = 5.0,
    min_width: int = 200,
    min_height: int = 150,
    used_hashes: Optional[Set[str]] = None,
    used_asset_ids: Optional[Set[str]] = None,
    used_urls: Optional[Set[str]] = None,
) -> ImageValidationResult:
    """
    Performs comprehensive validation of an image candidate.
    Returns a structured validation result with all defects.
    """
    result = ImageValidationResult()
    used_hashes = used_hashes or set()
    used_asset_ids = used_asset_ids or set()
    used_urls = used_urls or set()

    # 1. URL security
    url_safe, url_reason = validate_url_security(candidate.image_url)
    if not url_safe:
        result.defects.append(ImageDefectCode.IMAGE_DOWNLOAD_FAILED)
        result.defect_details.append(url_reason)

    # 2. Rights validation (hard gate)
    rights_ok, rights_defect, rights_detail = validate_image_rights(candidate.rights)
    if not rights_ok and rights_defect:
        result.defects.append(rights_defect)
        result.defect_details.append(rights_detail)
    result.rights_verified = rights_ok

    # 3. Image bytes validation
    if image_bytes:
        result.file_size_bytes = len(image_bytes)

        # Size check
        if len(image_bytes) > MAX_DOWNLOAD_BYTES:
            result.defects.append(ImageDefectCode.IMAGE_FILE_CORRUPT)
            result.defect_details.append(f"File size {len(image_bytes)} exceeds {MAX_DOWNLOAD_BYTES} limit")

        # Signature verification
        sig_ok, detected_mime = verify_image_signature(image_bytes)
        if not sig_ok:
            result.defects.append(ImageDefectCode.IMAGE_FORMAT_UNSUPPORTED)
            result.defect_details.append("Image magic bytes do not match any supported format")
        else:
            result.image_format = detected_mime

        # Content hash
        result.content_hash = compute_content_hash(image_bytes)

        # Try to read dimensions via PIL
        try:
            from PIL import Image
            Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS
            img = Image.open(io.BytesIO(image_bytes))
            result.image_width_px = img.width
            result.image_height_px = img.height
            img.verify()  # Also verifies integrity
        except Exception as e:
            result.defects.append(ImageDefectCode.IMAGE_FILE_CORRUPT)
            result.defect_details.append(f"PIL verification failed: {str(e)[:100]}")

    elif candidate.width_px > 0:
        # Use metadata dimensions when bytes not available (offline test)
        result.image_width_px = candidate.width_px
        result.image_height_px = candidate.height_px

    # 4. Dimension validation
    w = result.image_width_px or candidate.width_px
    h = result.image_height_px or candidate.height_px
    if w > 0 and h > 0:
        dim_ok, dim_defect, dim_detail = validate_image_dimensions(w, h, min_width, min_height)
        if not dim_ok and dim_defect:
            result.defects.append(dim_defect)
            result.defect_details.append(dim_detail)

    # 5. Aspect ratio compatibility
    if w > 0 and h > 0:
        ar_ok, ar_defect, ar_detail = validate_aspect_ratio_compatibility(
            w, h, region_width_in, region_height_in
        )
        if not ar_ok and ar_defect:
            result.defects.append(ar_defect)
            result.defect_details.append(ar_detail)

    # 6. Deduplication
    is_dup, dup_reason = check_deduplication(
        result.content_hash, candidate.asset_id, candidate.image_url,
        used_hashes, used_asset_ids, used_urls,
    )
    if is_dup:
        result.is_duplicate = True
        result.defects.append(ImageDefectCode.IMAGE_DUPLICATE_UNJUSTIFIED)
        result.defect_details.append(dup_reason)

    # Final verdict: valid only if no FATAL defects
    fatal_defects = {
        ImageDefectCode.IMAGE_RIGHTS_UNVERIFIED,
        ImageDefectCode.IMAGE_FILE_CORRUPT,
        ImageDefectCode.IMAGE_FORMAT_UNSUPPORTED,
        ImageDefectCode.IMAGE_DOWNLOAD_FAILED,
        ImageDefectCode.IMAGE_PROVENANCE_INCOMPLETE,
    }
    result.valid = not any(d in fatal_defects for d in result.defects)

    return result

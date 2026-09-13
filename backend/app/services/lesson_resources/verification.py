import re
import logging
from urllib.parse import urlparse
from typing import List, Optional
from .schemas import ResourceCandidate, VerificationLevel, ResourceQueryContext

logger = logging.getLogger("teachgenie.lesson_resources.verification")

VALID_URL_REGEX = re.compile(
    r"^https?://"  # http:// or https://
    r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"  # domain...
    r"localhost|"  # localhost...
    r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # ...or ip
    r"(?::\d+)?"  # optional port
    r"(?:/?|[/?]\S+)$", re.IGNORECASE
)


class ResourceVerificationEngine:
    """
    Guarantees that every candidate presented to learners is genuine, verified,
    and passes hard domain & concept relevance gating.
    """

    @classmethod
    def is_valid_url(cls, url: str) -> bool:
        if not url or not isinstance(url, str):
            return False
        if len(url) < 10 or len(url) > 2048:
            return False
        if not VALID_URL_REGEX.match(url):
            return False
        try:
            parsed = urlparse(url)
            return bool(parsed.scheme in ("http", "https") and parsed.netloc)
        except Exception:
            return False

    @classmethod
    def is_domain_compatible(cls, candidate: ResourceCandidate, context: Optional[ResourceQueryContext]) -> bool:
        """
        Hard domain compatibility gating.
        Rejects astronomy, biology taxonomy, sociology, generic vulnerability papers,
        and unrelated ML object classification when domain is CS / Python programming.
        """
        if not context:
            return True

        text = f"{candidate.title} {candidate.description} {candidate.author_or_channel}".lower()
        domain = (context.domain or "").lower()
        specialization = (context.specialization or "").lower()

        # 1. Computer Science / Software Engineering / Programming Checks
        if any(k in domain for k in ["computer_science", "software", "programming"]) or "programming" in specialization:
            # Check negative domain terms from context
            for neg in context.negative_terms:
                if neg.lower() in text:
                    # Unless explicitly part of a learning objective
                    if not any(neg.lower() in obj.lower() for obj in context.learning_objectives):
                        logger.info(f"[DomainGate] REJECTED | '{candidate.title[:45]}' matched negative term '{neg}'")
                        return False

            # Specific hard-rejections for astronomy/space
            astronomy_markers = [
                "astronomical", "astronomy", "jwst", "galaxy", "galaxies", "photometric classification",
                "celestial", "redshift", "stellar", "telescope", "cosmological", "astrophysics",
                "light curve", "solar system", "supernova", "spectral class", "hubble", "exoplanet",
                "planetary", "nebula", "interstellar", "astronomical object", "photometry"
            ]
            for am in astronomy_markers:
                if am in text:
                    logger.info(f"[DomainGate] REJECTED astronomy | '{candidate.title[:45]}' matched '{am}'")
                    return False

            # Specific hard-rejections for biology / taxonomy
            biology_markers = [
                "biological classification", "taxonomy", "taxonomic", "phylogenetic", "phylum",
                "botanical", "specimen", "species classification", "genus", "taxa", "clade",
                "fungi classification", "vertebrate", "invertebrate", "biological class"
            ]
            for bm in biology_markers:
                if bm in text:
                    logger.info(f"[DomainGate] REJECTED biology/taxonomy | '{candidate.title[:45]}' matched '{bm}'")
                    return False

            # Specific hard-rejections for sociology
            sociology_markers = [
                "social class", "socioeconomic", "caste system", "working class", "ruling class",
                "middle class", "bourgeoisie", "proletariat", "social classes"
            ]
            for sm in sociology_markers:
                if sm in text:
                    logger.info(f"[DomainGate] REJECTED sociology | '{candidate.title[:45]}' matched '{sm}'")
                    return False

            # If specialization is Python programming: reject generic Java vulnerability papers
            if "python" in specialization or "python" in context.normalized_topic.lower():
                java_vuln_markers = ["java vulnerability", "cve-", "deserialization vulnerability in java", "java class loader", "java bytecode"]
                for jv in java_vuln_markers:
                    if jv in text:
                        logger.info(f"[DomainGate] REJECTED Java vulnerability | '{candidate.title[:45]}' matched '{jv}'")
                        return False

            # Reject generic computer vision object detection/classification for OOP classes
            if any(k in context.normalized_topic.lower() for k in ["oop", "object-oriented", "classes and objects", "objects and classes", "object and class"]):
                cv_markers = ["yolo", "bounding box", "object detection in image", "object tracking", "segmentation mask", "lidar object", "point cloud object", "vehicle detection"]
                for cm in cv_markers:
                    if cm in text:
                        logger.info(f"[DomainGate] REJECTED CV object detection | '{candidate.title[:45]}' matched '{cm}'")
                        return False

        return True

    @classmethod
    def is_concept_compatible(cls, candidate: ResourceCandidate, context: Optional[ResourceQueryContext]) -> bool:
        """
        Hard concept compatibility gating.
        Ensures that a resource cannot be accepted merely because it contains generic words like
        'object' or 'class' in an unrelated domain.
        """
        if not context:
            return True

        text = f"{candidate.title} {candidate.description}".lower()

        # If canonical concept IDs are present, check concept tokens
        has_canonical_concept = False
        for cid in context.canonical_concept_ids:
            leaf = cid.split(".")[-1].lower()
            if len(leaf) > 2 and leaf in text:
                has_canonical_concept = True
                break

        # If domain is Python OOP: require that Python or OOP or a specific method/attribute concept is mentioned
        if "python" in (context.specialization or "").lower() or "python" in context.normalized_topic.lower():
            has_python_context = any(pk in text for pk in [
                "python", "py", "def ", "class ", "self", "__init__", "oop",
                "instantiat", "attribute", "method", "inheritance", "dunder",
                "constructor", "object-oriented", "polymorphism", "encapsulation"
            ])
            if not has_python_context:
                logger.info(f"[ConceptGate] REJECTED | '{candidate.title[:45]}' lacks Python/OOP programming context")
                return False

        # Check that candidate has meaningful semantic overlap with normalized topic or objectives
        topic_tokens = [w for w in re.split(r"[\s,:;\-]+", context.normalized_topic.lower()) if len(w) > 3 and w not in ["with", "from", "that", "this", "stage", "overview", "lecture"]]
        topic_token_matches = sum(1 for tt in topic_tokens if tt in text)

        if topic_token_matches == 0 and not has_canonical_concept:
            logger.info(f"[ConceptGate] REJECTED | '{candidate.title[:45]}' has zero topic or canonical concept matches")
            return False

        return True

    @classmethod
    def verify_candidate(cls, candidate: ResourceCandidate, context: Optional[ResourceQueryContext] = None) -> bool:
        """
        Validates a single candidate: URL, metadata, and domain/concept gating.
        """
        if not cls.is_valid_url(candidate.canonical_url):
            candidate.verified = False
            return False

        if not candidate.title or len(candidate.title.strip()) < 3:
            candidate.verified = False
            return False

        # Provider-specific integrity checks
        if candidate.provider == "youtube":
            if "youtube.com/watch?v=" not in candidate.canonical_url and "youtu.be/" not in candidate.canonical_url:
                candidate.verified = False
                return False
        elif candidate.provider == "arxiv":
            if "arxiv.org/" not in candidate.canonical_url:
                candidate.verified = False
                return False
        elif candidate.provider == "semantic_scholar":
            if "semanticscholar.org" not in candidate.canonical_url and "doi.org" not in candidate.canonical_url:
                candidate.verified = False
                return False

        # Hard Domain and Concept Relevance Gating
        if context:
            if not cls.is_domain_compatible(candidate, context):
                candidate.verified = False
                return False
            if not cls.is_concept_compatible(candidate, context):
                candidate.verified = False
                return False

        candidate.verified = True
        return True

    @classmethod
    def filter_and_verify(
        cls,
        candidates: List[ResourceCandidate],
        context: Optional[ResourceQueryContext] = None
    ) -> List[ResourceCandidate]:
        """
        Deduplicates by URL and verifies all candidates against integrity and domain gates.
        """
        verified_list: List[ResourceCandidate] = []
        seen_urls = set()

        for c in candidates:
            norm_url = c.canonical_url.split("#")[0].rstrip("/")
            if norm_url in seen_urls:
                continue

            if cls.verify_candidate(c, context=context):
                seen_urls.add(norm_url)
                c.canonical_url = norm_url
                verified_list.append(c)

        return verified_list


# Module-level aliases fulfilling Requirement 2
is_domain_compatible = ResourceVerificationEngine.is_domain_compatible
is_concept_compatible = ResourceVerificationEngine.is_concept_compatible


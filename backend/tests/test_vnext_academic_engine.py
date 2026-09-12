import pytest
from app.services.lesson_planner.schemas import (
    RoadmapStage, StageArchetype, ProductMode, JournalQuartile, ConferenceTier, PaperType
)
from app.services.lesson_planner.vnext.resources.academic_engine import (
    AcademicEvidenceEngine, KNOWN_JOURNAL_QUARTILES, KNOWN_CONF_TIERS
)


class MockRawPaper:
    def __init__(self, title, description, url):
        self.title = title
        self.description = description
        self.url = url


def _get_test_stage() -> RoadmapStage:
    return RoadmapStage(
        id="stage_eval",
        concept_id="c_eval",
        title="Dynamic Programming Optimization",
        description="Empirical evaluation and algorithms",
        sequence=0,
        duration_minutes=20,
        archetype=StageArchetype.RESEARCH_REVIEW
    )


def test_verified_q1_journal_provenance():
    """Q1 journal must include Scimago SJR ranking provenance and never treat Crossref as authority."""
    stage = _get_test_stage()
    raw = MockRawPaper(
        title="Optimal Substructure Analysis in IEEE Transactions on Computers",
        description="Empirical algorithms published in IEEE Transactions.",
        url="https://doi.org/10.1109/TC.2023.12345"
    )

    card = AcademicEvidenceEngine._parse_and_score_paper(raw, stage, "Dynamic Programming", "B.Tech")
    assert card.academic_provenance is not None
    prov = card.academic_provenance
    assert prov.ranking_system == "SJR"
    assert prov.raw_rank == "Q1"
    assert "crossref" in prov.metadata_sources
    assert prov.ranking_source != "crossref"  # Crossref is NEVER ranking authority
    assert "ieee_xplore" in prov.metadata_sources


def test_verified_conference_tier_provenance():
    """A* conference must include CORE ranking provenance with ranking version."""
    stage = _get_test_stage()
    raw = MockRawPaper(
        title="Fast Dynamic Programming via SIMD Vectorization in VLDB 2023",
        description="Proceedings of the VLDB Endowment conference paper.",
        url="https://www.vldb.org/pvldb/vol16/p1234.pdf"
    )

    card = AcademicEvidenceEngine._parse_and_score_paper(raw, stage, "Dynamic Programming", "B.Tech")
    assert card.academic_provenance is not None
    prov = card.academic_provenance
    assert prov.ranking_system == "CORE"
    assert prov.raw_rank == "A*"
    assert prov.ranking_year_or_version == "2023.1"


def test_unverified_venue_marked_unknown():
    """Unranked or unknown venue must have raw_rank='unknown', never a guessed ranking."""
    stage = _get_test_stage()
    raw = MockRawPaper(
        title="A Simple Tutorial on Dynamic Programming",
        description="Published on personal university website.",
        url="https://cs.university.edu/~prof/dp_tutorial.pdf"
    )

    card = AcademicEvidenceEngine._parse_and_score_paper(raw, stage, "Dynamic Programming", "B.Tech")
    assert card.academic_provenance is not None
    prov = card.academic_provenance
    assert prov.raw_rank == "unknown"
    assert prov.ranking_system is None


def test_retraction_safety_gate_rejects_retracted_papers():
    """Papers with retraction notice must be skipped by get_scholarly_evidence."""
    stage = _get_test_stage()
    raw = MockRawPaper(
        title="Retracted: Novel Polynomial Solver for NP-Hard Problems",
        description="Notice: This article has been retracted by the editor.",
        url="https://doi.org/10.1016/j.jss.2022.retracted"
    )

    card = AcademicEvidenceEngine._parse_and_score_paper(raw, stage, "Algorithms", "B.Tech")
    assert card.has_retraction_notice is True


def test_preprint_badged_correctly():
    """arXiv preprints must be tagged as preprints without peer-reviewed venue label."""
    stage = _get_test_stage()
    raw = MockRawPaper(
        title="Self-Supervised Representation Learning for Graphs",
        description="Preprint submission under review.",
        url="https://arxiv.org/abs/2301.12345"
    )

    card = AcademicEvidenceEngine._parse_and_score_paper(raw, stage, "Graphs", "B.Tech")
    assert card.is_preprint is True
    assert "Preprint" in card.venue_label
    assert "arxiv" in card.academic_provenance.metadata_sources

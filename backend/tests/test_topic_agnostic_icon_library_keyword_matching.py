"""
Test: Topic-agnostic icon library keyword matching
====================================================
Validates:
1. Medical terms → medical icons
2. Financial terms → finance icons
3. Unmatched terms → None (stock photo fallback)
4. Multi-word tag matching works
"""
import pytest
from app.services.presentation_engine.renderers.topic_icons import resolve_topic_icon


class TestTopicIconResolution:
    def test_medical_terms_resolve_to_medical_icons(self):
        result = resolve_topic_icon("Medical diagnosis with deep learning")
        assert result is not None
        assert "medical" in result.lower() or "dna" in result.lower() or "heartbeat" in result.lower()

    def test_financial_terms_resolve_to_finance_icons(self):
        result = resolve_topic_icon("Financial fraud detection and market analysis")
        assert result is not None
        assert "chart" in result.lower() or "coin" in result.lower()

    def test_agriculture_terms_resolve_to_agriculture_icons(self):
        result = resolve_topic_icon("Agricultural crop monitoring and farming")
        assert result is not None
        assert "wheat" in result.lower() or "grain" in result.lower()

    def test_education_terms_resolve_to_education_icons(self):
        result = resolve_topic_icon("University education and academic learning")
        assert result is not None
        assert "graduation" in result.lower() or "book" in result.lower()

    def test_unmatched_terms_return_none(self):
        result = resolve_topic_icon("xyzzy flurbnik qwazle")
        assert result is None

    def test_empty_string_returns_none(self):
        result = resolve_topic_icon("")
        assert result is None

    def test_none_returns_none(self):
        result = resolve_topic_icon(None)
        assert result is None

    def test_multi_word_tag_matching(self):
        """Multi-word tags like 'deep learning' should get bonus scores."""
        result = resolve_topic_icon("deep learning neural network training pipeline")
        assert result is not None
        assert "neural" in result.lower()

    def test_cybersecurity_resolves(self):
        result = resolve_topic_icon("cybersecurity encryption firewall protection")
        assert result is not None
        assert "shield" in result.lower()

    def test_environment_resolves(self):
        result = resolve_topic_icon("sustainable ecology and green energy conservation")
        assert result is not None
        assert "leaf" in result.lower() or "solar" in result.lower()

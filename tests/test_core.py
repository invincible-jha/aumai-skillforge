"""Comprehensive tests for aumai-skillforge core module."""

from __future__ import annotations

import pytest

from aumai_skillforge.core import SkillComposer, SkillNotFoundError, SkillRegistry
from aumai_skillforge.models import Skill, SkillComposition, SkillSearchResult


# ---------------------------------------------------------------------------
# SkillRegistry tests
# ---------------------------------------------------------------------------


class TestSkillRegistry:
    """Tests for SkillRegistry."""

    def test_register_and_get(self, nlp_skill: Skill) -> None:
        """register() stores a skill retrievable by get()."""
        reg = SkillRegistry()
        reg.register(nlp_skill)
        retrieved = reg.get("nlp-sentiment")
        assert retrieved.skill_id == "nlp-sentiment"
        assert retrieved.name == "Sentiment Analyzer"

    def test_get_missing_raises(self) -> None:
        """get() raises SkillNotFoundError for unknown skill_id."""
        reg = SkillRegistry()
        with pytest.raises(SkillNotFoundError):
            reg.get("non-existent-skill")

    def test_register_overwrites_existing(self, nlp_skill: Skill) -> None:
        """Registering a skill with an existing ID updates the entry."""
        reg = SkillRegistry()
        reg.register(nlp_skill)
        updated = nlp_skill.model_copy(update={"name": "Updated NLP"})
        reg.register(updated)
        assert reg.get("nlp-sentiment").name == "Updated NLP"

    def test_search_by_query_term(self, registry: SkillRegistry) -> None:
        """search() returns skills matching a query term."""
        results = registry.search(query="sentiment")
        skill_ids = [r.skill.skill_id for r in results]
        assert "nlp-sentiment" in skill_ids

    def test_search_empty_query_returns_all(self, registry: SkillRegistry) -> None:
        """search() with empty query returns all registered skills."""
        results = registry.search(query="")
        assert len(results) == 3

    def test_search_by_tag(self, registry: SkillRegistry) -> None:
        """search() with tags filter returns only matching skills."""
        results = registry.search(query="", tags=["vision"])
        assert len(results) == 1
        assert results[0].skill.skill_id == "image-classifier"

    def test_search_by_multiple_tags(self, registry: SkillRegistry) -> None:
        """search() requires all specified tags to be present."""
        results = registry.search(query="", tags=["nlp", "summarization"])
        assert len(results) == 1
        assert results[0].skill.skill_id == "text-summarizer"

    def test_search_tag_not_matching_returns_empty(
        self, registry: SkillRegistry
    ) -> None:
        """search() returns empty list when no skills match the tag filter."""
        results = registry.search(query="", tags=["robotics"])
        assert results == []

    def test_search_relevance_sorted_descending(
        self, registry: SkillRegistry
    ) -> None:
        """search() results are sorted by descending relevance."""
        results = registry.search(query="nlp text")
        for i in range(len(results) - 1):
            assert results[i].relevance >= results[i + 1].relevance

    def test_search_relevance_in_range(self, registry: SkillRegistry) -> None:
        """search() relevance scores are between 0.0 and 1.0."""
        results = registry.search(query="nlp")
        for result in results:
            assert 0.0 <= result.relevance <= 1.0

    def test_search_no_match_returns_empty(self, registry: SkillRegistry) -> None:
        """search() returns empty list when query matches nothing."""
        results = registry.search(query="xyzzy_quantum_unicorn")
        assert results == []

    def test_search_author_match(self, registry: SkillRegistry) -> None:
        """search() matches against author field."""
        results = registry.search(query="alice")
        assert any(r.skill.skill_id == "nlp-sentiment" for r in results)

    def test_increment_downloads(self, registry: SkillRegistry) -> None:
        """increment_downloads() increases the download count by 1."""
        original_downloads = registry.get("nlp-sentiment").downloads
        registry.increment_downloads("nlp-sentiment")
        assert registry.get("nlp-sentiment").downloads == original_downloads + 1

    def test_increment_downloads_missing_skill_silently_ignored(
        self, registry: SkillRegistry
    ) -> None:
        """increment_downloads() does nothing for unknown skill_id."""
        registry.increment_downloads("non-existent-skill")  # Should not raise

    def test_increment_downloads_multiple_times(
        self, registry: SkillRegistry
    ) -> None:
        """download counter correctly increments across multiple calls."""
        for _ in range(5):
            registry.increment_downloads("nlp-sentiment")
        assert registry.get("nlp-sentiment").downloads == 47  # 42 + 5


# ---------------------------------------------------------------------------
# SkillComposer tests
# ---------------------------------------------------------------------------


class TestSkillComposer:
    """Tests for SkillComposer."""

    def test_compose_single_skill(
        self, composer: SkillComposer, registry: SkillRegistry
    ) -> None:
        """compose() creates a composition with a single skill."""
        comp = composer.compose(
            skills=["nlp-sentiment"],
            pipeline=[{"skill_id": "nlp-sentiment", "step": 0}],
            name="single-pipeline",
        )
        assert comp.name == "single-pipeline"
        assert comp.skills == ["nlp-sentiment"]

    def test_compose_two_skills(self, composer: SkillComposer) -> None:
        """compose() creates a linear pipeline of two skills."""
        comp = composer.compose(
            skills=["nlp-sentiment", "text-summarizer"],
            pipeline=[
                {"skill_id": "nlp-sentiment", "step": 0},
                {"skill_id": "text-summarizer", "step": 1},
            ],
            name="nlp-pipeline",
        )
        assert len(comp.skills) == 2

    def test_compose_raises_for_unknown_skill(
        self, composer: SkillComposer
    ) -> None:
        """compose() raises SkillNotFoundError for unregistered skill IDs."""
        with pytest.raises(SkillNotFoundError):
            composer.compose(
                skills=["nlp-sentiment", "ghost-skill"],
                pipeline=[],
            )

    def test_compose_default_name(self, composer: SkillComposer) -> None:
        """compose() uses 'composed-pipeline' as default name."""
        comp = composer.compose(skills=["nlp-sentiment"], pipeline=[])
        assert comp.name == "composed-pipeline"

    def test_validate_composition_empty_skills_returns_issue(
        self, composer: SkillComposer
    ) -> None:
        """validate_composition() returns an issue for empty skills list."""
        comp = SkillComposition(name="empty", skills=[], pipeline=[])
        issues = composer.validate_composition(comp)
        assert any("no skills" in issue.lower() for issue in issues)

    def test_validate_composition_compatible_schemas_no_issues(
        self, composer: SkillComposer
    ) -> None:
        """validate_composition() returns no issues for compatible output->input schemas."""
        comp = composer.compose(
            skills=["nlp-sentiment", "text-summarizer"],
            pipeline=[],
            name="compatible",
        )
        issues = composer.validate_composition(comp)
        assert issues == []

    def test_validate_composition_unknown_skill_in_composition(
        self, composer: SkillComposer
    ) -> None:
        """validate_composition() reports issues for unregistered skills in a composition."""
        comp = SkillComposition(
            name="broken",
            skills=["nlp-sentiment", "does-not-exist"],
            pipeline=[],
        )
        issues = composer.validate_composition(comp)
        assert any("does-not-exist" in issue for issue in issues)

    def test_validate_composition_incompatible_schemas(
        self, registry: SkillRegistry, composer: SkillComposer
    ) -> None:
        """validate_composition() detects missing required fields between steps."""
        # image-classifier has no output schema, text-summarizer requires 'score'
        comp = SkillComposition(
            name="incompatible",
            skills=["image-classifier", "text-summarizer"],
            pipeline=[],
        )
        issues = composer.validate_composition(comp)
        assert len(issues) > 0

    def test_composition_description_stored(self, composer: SkillComposer) -> None:
        """compose() stores the provided description."""
        comp = composer.compose(
            skills=["nlp-sentiment"],
            pipeline=[],
            description="An NLP pipeline for analysis",
        )
        assert comp.description == "An NLP pipeline for analysis"

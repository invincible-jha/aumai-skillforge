"""Shared test fixtures for aumai-skillforge."""

from __future__ import annotations

import pytest

from aumai_skillforge.core import SkillComposer, SkillRegistry
from aumai_skillforge.models import Skill


@pytest.fixture()
def nlp_skill() -> Skill:
    """Return an NLP skill for sentiment analysis."""
    return Skill(
        skill_id="nlp-sentiment",
        name="Sentiment Analyzer",
        description="Analyze text sentiment and return a score",
        version="1.0.0",
        author="alice",
        tags=["nlp", "sentiment", "text"],
        input_schema={
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
        output_schema={
            "type": "object",
            "properties": {"score": {"type": "number"}, "label": {"type": "string"}},
        },
        downloads=42,
    )


@pytest.fixture()
def summarizer_skill() -> Skill:
    """Return a text summarization skill."""
    return Skill(
        skill_id="text-summarizer",
        name="Text Summarizer",
        description="Summarize long text documents into short summaries",
        version="0.2.0",
        author="bob",
        tags=["nlp", "summarization", "text"],
        input_schema={
            "type": "object",
            "properties": {"score": {"type": "number"}, "label": {"type": "string"}},
            "required": ["score"],
        },
        output_schema={
            "type": "object",
            "properties": {"summary": {"type": "string"}},
        },
        downloads=10,
    )


@pytest.fixture()
def image_skill() -> Skill:
    """Return an image classification skill."""
    return Skill(
        skill_id="image-classifier",
        name="Image Classifier",
        description="Classify images into categories",
        version="0.1.0",
        author="carol",
        tags=["vision", "classification", "image"],
        downloads=5,
    )


@pytest.fixture()
def registry(nlp_skill: Skill, summarizer_skill: Skill, image_skill: Skill) -> SkillRegistry:
    """Return a SkillRegistry pre-populated with three skills."""
    reg = SkillRegistry()
    reg.register(nlp_skill)
    reg.register(summarizer_skill)
    reg.register(image_skill)
    return reg


@pytest.fixture()
def composer(registry: SkillRegistry) -> SkillComposer:
    """Return a SkillComposer backed by the populated registry."""
    return SkillComposer(registry=registry)

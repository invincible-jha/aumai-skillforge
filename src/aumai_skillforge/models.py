"""Pydantic models for aumai-skillforge."""

from __future__ import annotations

from pydantic import BaseModel, Field

__all__ = [
    "Skill",
    "SkillComposition",
    "SkillSearchResult",
]


class Skill(BaseModel):
    """A composable agent skill in the marketplace."""

    skill_id: str
    name: str
    description: str
    version: str = "0.1.0"
    author: str
    input_schema: dict[str, object] = Field(default_factory=dict, description="JSON Schema for inputs.")
    output_schema: dict[str, object] = Field(default_factory=dict, description="JSON Schema for outputs.")
    tags: list[str] = Field(default_factory=list)
    downloads: int = Field(default=0, ge=0)


class SkillComposition(BaseModel):
    """A named pipeline composed of multiple skills."""

    name: str
    skills: list[str] = Field(description="Ordered list of skill_ids.")
    pipeline: list[dict[str, object]] = Field(
        default_factory=list,
        description="Step-by-step pipeline configuration.",
    )
    description: str = ""


class SkillSearchResult(BaseModel):
    """A search result pairing a skill with a relevance score."""

    skill: Skill
    relevance: float = Field(ge=0.0, le=1.0)

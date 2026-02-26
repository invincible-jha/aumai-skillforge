"""FastAPI application for aumai-skillforge."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from aumai_skillforge.core import SkillComposer, SkillNotFoundError, SkillRegistry
from aumai_skillforge.models import Skill, SkillComposition, SkillSearchResult

app = FastAPI(title="AumAI Skill Marketplace", version="0.1.0")

_registry = SkillRegistry()
_composer = SkillComposer(registry=_registry)


class CompositionRequest(BaseModel):
    """Request body for creating a skill composition."""

    skills: list[str]
    pipeline: list[dict[str, object]]
    name: str = "composition"
    description: str = ""


@app.get("/api/skills", response_model=list[SkillSearchResult])
def list_skills(query: str = "", tags: str = "") -> list[SkillSearchResult]:
    """List and search skills. `tags` is a comma-separated list."""
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None
    return _registry.search(query=query, tags=tag_list)


@app.post("/api/skills", response_model=Skill, status_code=201)
def register_skill(skill: Skill) -> Skill:
    """Register a new skill in the marketplace."""
    _registry.register(skill)
    return skill


@app.get("/api/skills/{skill_id}", response_model=Skill)
def get_skill(skill_id: str) -> Skill:
    """Retrieve a skill by ID."""
    try:
        return _registry.get(skill_id)
    except SkillNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Skill '{skill_id}' not found") from exc


@app.post("/api/compositions", response_model=SkillComposition, status_code=201)
def create_composition(request: CompositionRequest) -> SkillComposition:
    """Create a skill composition pipeline."""
    try:
        return _composer.compose(
            skills=request.skills,
            pipeline=request.pipeline,
            name=request.name,
            description=request.description,
        )
    except SkillNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

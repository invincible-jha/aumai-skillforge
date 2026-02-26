"""Core logic for aumai-skillforge."""

from __future__ import annotations

import re

from aumai_skillforge.models import Skill, SkillComposition, SkillSearchResult

__all__ = ["SkillRegistry", "SkillComposer"]


class SkillNotFoundError(KeyError):
    """Raised when a requested skill is not in the registry."""


class SkillRegistry:
    """In-memory registry for agent skills."""

    def __init__(self) -> None:
        self._skills: dict[str, Skill] = {}

    def register(self, skill: Skill) -> None:
        """Register or update a skill in the registry.

        Args:
            skill: The skill to register.
        """
        self._skills[skill.skill_id] = skill

    def search(
        self,
        query: str,
        tags: list[str] | None = None,
    ) -> list[SkillSearchResult]:
        """Search for skills by query text and optional tag filter.

        Relevance is computed as a simple TF-style score based on
        query term matches in the name, description, and tags.

        Args:
            query: Search query string.
            tags: Optional list of required tags.

        Returns:
            List of SkillSearchResult sorted by descending relevance.
        """
        query_terms = re.findall(r"\w+", query.lower())
        results: list[SkillSearchResult] = []

        for skill in self._skills.values():
            if tags:
                skill_tags_lower = [t.lower() for t in skill.tags]
                if not all(t.lower() in skill_tags_lower for t in tags):
                    continue

            if not query_terms:
                results.append(SkillSearchResult(skill=skill, relevance=1.0))
                continue

            searchable = " ".join(
                [skill.name, skill.description, skill.author] + skill.tags
            ).lower()

            hits = sum(1 for term in query_terms if term in searchable)
            relevance = min(hits / len(query_terms), 1.0) if query_terms else 0.0
            if relevance > 0:
                results.append(SkillSearchResult(skill=skill, relevance=round(relevance, 3)))

        results.sort(key=lambda r: (r.relevance, r.skill.downloads), reverse=True)
        return results

    def get(self, skill_id: str) -> Skill:
        """Retrieve a skill by its ID.

        Args:
            skill_id: The unique skill identifier.

        Returns:
            The Skill.

        Raises:
            SkillNotFoundError: If the skill is not registered.
        """
        try:
            return self._skills[skill_id]
        except KeyError as exc:
            raise SkillNotFoundError(skill_id) from exc

    def increment_downloads(self, skill_id: str) -> None:
        """Increment download counter for a skill.

        Args:
            skill_id: The skill identifier.
        """
        if skill_id in self._skills:
            skill = self._skills[skill_id]
            self._skills[skill_id] = skill.model_copy(
                update={"downloads": skill.downloads + 1}
            )


class SkillComposer:
    """Compose multiple skills into a sequential pipeline."""

    def __init__(self, registry: SkillRegistry) -> None:
        self._registry = registry

    def compose(
        self,
        skills: list[str],
        pipeline: list[dict[str, object]],
        name: str = "composed-pipeline",
        description: str = "",
    ) -> SkillComposition:
        """Chain skills into a named pipeline composition.

        Args:
            skills: Ordered list of skill_ids to compose.
            pipeline: Step-by-step configuration for each skill connection.
            name: Human-readable name for the composition.
            description: Optional description.

        Returns:
            A SkillComposition.

        Raises:
            SkillNotFoundError: If any skill_id in `skills` is not registered.
        """
        for skill_id in skills:
            self._registry.get(skill_id)  # validates each skill exists

        return SkillComposition(
            name=name,
            skills=skills,
            pipeline=pipeline,
            description=description,
        )

    def validate_composition(self, composition: SkillComposition) -> list[str]:
        """Check schema compatibility between consecutive skills in a pipeline.

        Validates that the output_schema of each skill is compatible with
        the input_schema of the next skill by comparing top-level property keys.

        Args:
            composition: The SkillComposition to validate.

        Returns:
            List of validation issue strings. Empty list means valid.
        """
        issues: list[str] = []

        if not composition.skills:
            issues.append("Composition has no skills.")
            return issues

        for skill_id in composition.skills:
            try:
                self._registry.get(skill_id)
            except SkillNotFoundError:
                issues.append(f"Skill '{skill_id}' is not registered.")

        if issues:
            return issues

        # Check output->input compatibility for consecutive pairs
        for idx in range(len(composition.skills) - 1):
            current_id = composition.skills[idx]
            next_id = composition.skills[idx + 1]
            current_skill = self._registry.get(current_id)
            next_skill = self._registry.get(next_id)

            out_schema = current_skill.output_schema or {}
            in_schema = next_skill.input_schema or {}
            out_props_raw = out_schema.get("properties", {})
            out_props = set(out_props_raw.keys()) if isinstance(out_props_raw, dict) else set()
            in_props_raw = in_schema.get("required", [])
            in_props = set(in_props_raw) if isinstance(in_props_raw, list) else set()

            if in_props and not in_props.issubset(out_props):
                missing = in_props - out_props
                issues.append(
                    f"Skill '{current_id}' output is missing fields required by "
                    f"'{next_id}': {sorted(missing)}"
                )

        return issues

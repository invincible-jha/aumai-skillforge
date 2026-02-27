"""Quickstart examples for aumai-skillforge.

Demonstrates skill registration, tag-based and text search, download tracking,
pipeline composition, and schema-compatibility validation.

Run this file directly to verify your installation:

    python examples/quickstart.py

No external services or API keys are required — everything runs in-memory.
"""

from aumai_skillforge.core import SkillComposer, SkillNotFoundError, SkillRegistry
from aumai_skillforge.models import Skill, SkillComposition, SkillSearchResult


# ---------------------------------------------------------------------------
# Demo 1: Register skills and search the marketplace
# ---------------------------------------------------------------------------


def demo_register_and_search() -> None:
    """Register a set of skills then perform text and tag-based searches."""
    print("\n--- Demo 1: Register and Search ---")

    registry = SkillRegistry()

    # Register three skills with distinct capabilities and tags
    registry.register(
        Skill(
            skill_id="web-search-v1",
            name="Web Search",
            description="Search the web and return ranked results for a query.",
            version="1.0.0",
            author="aumai-team",
            tags=["search", "web", "retrieval"],
            downloads=1240,
            input_schema={
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
            output_schema={
                "type": "object",
                "properties": {"results": {"type": "array"}},
            },
        )
    )

    registry.register(
        Skill(
            skill_id="text-summariser-v1",
            name="Text Summariser",
            description="Summarise a long document into a concise paragraph.",
            version="1.0.0",
            author="aumai-team",
            tags=["nlp", "summarisation", "text"],
            downloads=870,
            input_schema={
                "type": "object",
                "properties": {"results": {"type": "array"}},
                "required": ["results"],
            },
            output_schema={
                "type": "object",
                "properties": {"summary": {"type": "string"}},
            },
        )
    )

    registry.register(
        Skill(
            skill_id="sentiment-analyser-v1",
            name="Sentiment Analyser",
            description="Classify the sentiment of text as positive, negative, or neutral.",
            version="0.9.0",
            author="community",
            tags=["nlp", "classification", "sentiment"],
            downloads=420,
            input_schema={
                "type": "object",
                "properties": {"summary": {"type": "string"}},
                "required": ["summary"],
            },
            output_schema={
                "type": "object",
                "properties": {"sentiment": {"type": "string"}, "score": {"type": "number"}},
            },
        )
    )

    # Free-text search across name, description, and tags
    results: list[SkillSearchResult] = registry.search("summarise text documents")
    print(f"Search 'summarise text documents' -> {len(results)} result(s)")
    for result in results:
        print(f"  [{result.relevance:.3f}] {result.skill.name} (id={result.skill.skill_id})")

    # Tag filter: only skills tagged "nlp"
    nlp_results = registry.search("", tags=["nlp"])
    print(f"\nTag filter 'nlp' -> {len(nlp_results)} result(s)")
    for result in nlp_results:
        print(f"  {result.skill.name} | tags={result.skill.tags}")

    # Direct lookup
    skill = registry.get("web-search-v1")
    print(f"\nDirect lookup: {skill.name} v{skill.version} by {skill.author}")


# ---------------------------------------------------------------------------
# Demo 2: Download tracking
# ---------------------------------------------------------------------------


def demo_download_tracking() -> None:
    """Show how the registry tracks download counts per skill."""
    print("\n--- Demo 2: Download Tracking ---")

    registry = SkillRegistry()
    registry.register(
        Skill(
            skill_id="code-executor-v1",
            name="Code Executor",
            description="Safely execute Python code snippets in a sandboxed environment.",
            version="1.2.0",
            author="aumai-team",
            tags=["code", "execution", "sandbox"],
            downloads=0,
        )
    )

    skill_before = registry.get("code-executor-v1")
    print(f"Downloads before: {skill_before.downloads}")

    # Simulate three downloads
    for _ in range(3):
        registry.increment_downloads("code-executor-v1")

    skill_after = registry.get("code-executor-v1")
    print(f"Downloads after 3 increments: {skill_after.downloads}")

    # Incrementing a non-existent ID is a silent no-op (no error)
    registry.increment_downloads("does-not-exist")
    print("Incrementing unknown skill_id: no error raised (safe no-op)")


# ---------------------------------------------------------------------------
# Demo 3: Compose a multi-skill pipeline
# ---------------------------------------------------------------------------


def demo_pipeline_composition() -> None:
    """Chain three skills into a named pipeline and inspect the composition."""
    print("\n--- Demo 3: Pipeline Composition ---")

    registry = SkillRegistry()

    # Register skills needed for the pipeline
    for skill in [
        Skill(
            skill_id="web-search-v1",
            name="Web Search",
            description="Search the web.",
            author="aumai-team",
            tags=["search"],
            input_schema={
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
            output_schema={
                "type": "object",
                "properties": {"results": {"type": "array"}},
            },
        ),
        Skill(
            skill_id="text-summariser-v1",
            name="Text Summariser",
            description="Summarise text.",
            author="aumai-team",
            tags=["nlp"],
            input_schema={
                "type": "object",
                "properties": {"results": {"type": "array"}},
                "required": ["results"],
            },
            output_schema={
                "type": "object",
                "properties": {"summary": {"type": "string"}},
            },
        ),
        Skill(
            skill_id="sentiment-analyser-v1",
            name="Sentiment Analyser",
            description="Classify sentiment.",
            author="community",
            tags=["nlp"],
            input_schema={
                "type": "object",
                "properties": {"summary": {"type": "string"}},
                "required": ["summary"],
            },
            output_schema={
                "type": "object",
                "properties": {"sentiment": {"type": "string"}},
            },
        ),
    ]:
        registry.register(skill)

    composer = SkillComposer(registry)

    pipeline_steps = [
        {"step": 1, "skill_id": "web-search-v1", "output_key": "results"},
        {"step": 2, "skill_id": "text-summariser-v1", "input_key": "results", "output_key": "summary"},
        {"step": 3, "skill_id": "sentiment-analyser-v1", "input_key": "summary"},
    ]

    composition: SkillComposition = composer.compose(
        skills=["web-search-v1", "text-summariser-v1", "sentiment-analyser-v1"],
        pipeline=pipeline_steps,
        name="web-search-summarise-sentiment",
        description="Search the web, summarise results, then classify sentiment.",
    )

    print(f"Composition name : {composition.name}")
    print(f"Skill count      : {len(composition.skills)}")
    print(f"Pipeline steps   : {len(composition.pipeline)}")
    print(f"Description      : {composition.description}")
    for i, skill_id in enumerate(composition.skills, 1):
        print(f"  Step {i}: {skill_id}")


# ---------------------------------------------------------------------------
# Demo 4: Schema-compatibility validation
# ---------------------------------------------------------------------------


def demo_schema_validation() -> None:
    """Validate that consecutive skills have compatible output/input schemas."""
    print("\n--- Demo 4: Schema Validation ---")

    registry = SkillRegistry()
    composer = SkillComposer(registry)

    # Compatible pipeline: output of step 1 supplies required inputs of step 2
    registry.register(
        Skill(
            skill_id="data-fetch-v1",
            name="Data Fetcher",
            description="Fetch structured data from an API.",
            author="aumai-team",
            tags=["data"],
            output_schema={
                "type": "object",
                "properties": {"records": {"type": "array"}, "total": {"type": "integer"}},
            },
        )
    )
    registry.register(
        Skill(
            skill_id="data-transform-v1",
            name="Data Transformer",
            description="Transform and normalise data records.",
            author="aumai-team",
            tags=["data"],
            input_schema={
                "type": "object",
                "properties": {"records": {"type": "array"}},
                "required": ["records"],
            },
            output_schema={
                "type": "object",
                "properties": {"transformed": {"type": "array"}},
            },
        )
    )

    valid_composition = composer.compose(
        skills=["data-fetch-v1", "data-transform-v1"],
        pipeline=[],
        name="fetch-then-transform",
    )
    issues = composer.validate_composition(valid_composition)
    print(f"Valid composition issues : {issues or 'none — schemas are compatible'}")

    # Incompatible pipeline: step 2 requires 'missing_field' not in step 1 output
    registry.register(
        Skill(
            skill_id="bad-consumer-v1",
            name="Bad Consumer",
            description="Requires a field that upstream does not produce.",
            author="test",
            tags=["test"],
            input_schema={
                "type": "object",
                "required": ["missing_field"],
            },
        )
    )
    bad_composition = composer.compose(
        skills=["data-fetch-v1", "bad-consumer-v1"],
        pipeline=[],
        name="broken-pipeline",
    )
    bad_issues = composer.validate_composition(bad_composition)
    print(f"Invalid composition issues: {bad_issues}")


# ---------------------------------------------------------------------------
# Demo 5: Error handling for missing skills
# ---------------------------------------------------------------------------


def demo_error_handling() -> None:
    """Show that SkillNotFoundError is raised for unknown skill IDs."""
    print("\n--- Demo 5: Error Handling ---")

    registry = SkillRegistry()
    composer = SkillComposer(registry)

    # Direct lookup of a non-existent skill
    try:
        registry.get("non-existent-skill")
    except SkillNotFoundError as error:
        print(f"SkillNotFoundError raised for get(): {error}")

    # Composing with a missing skill also raises SkillNotFoundError
    try:
        composer.compose(
            skills=["missing-skill-id"],
            pipeline=[],
            name="will-fail",
        )
    except SkillNotFoundError as error:
        print(f"SkillNotFoundError raised for compose(): {error}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Run all aumai-skillforge quickstart demos."""
    print("=== aumai-skillforge Quickstart ===")
    demo_register_and_search()
    demo_download_tracking()
    demo_pipeline_composition()
    demo_schema_validation()
    demo_error_handling()
    print("\nAll demos completed successfully.")


if __name__ == "__main__":
    main()

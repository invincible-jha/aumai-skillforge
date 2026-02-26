"""CLI entry point for aumai-skillforge."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

import yaml  # type: ignore[import-untyped]

from aumai_skillforge.core import SkillComposer, SkillRegistry
from aumai_skillforge.models import Skill

_registry = SkillRegistry()
_composer = SkillComposer(registry=_registry)


@click.group()
@click.version_option()
def main() -> None:
    """AumAI SkillForge — Agent skill marketplace and composition CLI."""


@main.command("search")
@click.option("--query", default="", show_default=True, help="Search query.")
@click.option("--tags", default="", help="Comma-separated required tags.")
def search(query: str, tags: str) -> None:
    """Search for skills in the registry."""
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None
    results = _registry.search(query=query, tags=tag_list)
    if not results:
        click.echo("No skills found.")
        return
    for result in results:
        skill = result.skill
        click.echo(
            f"[{skill.skill_id}] {skill.name} v{skill.version}  "
            f"relevance={result.relevance:.2f}  tags={','.join(skill.tags)}"
        )


@main.command("register")
@click.option(
    "--config",
    required=True,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Path to skill YAML/JSON config file.",
)
def register(config: Path) -> None:
    """Register a skill from a config file."""
    raw = config.read_text(encoding="utf-8")
    if config.suffix in {".yaml", ".yml"}:
        data: dict[str, object] = yaml.safe_load(raw)
    else:
        data = json.loads(raw)
    skill = Skill.model_validate(data)
    _registry.register(skill)
    click.echo(f"Registered skill '{skill.name}' (ID: {skill.skill_id}).")


@main.command("compose")
@click.option("--skills", required=True, help="Comma-separated skill IDs.")
@click.option(
    "--output",
    required=True,
    type=click.Path(dir_okay=False, path_type=Path),
    help="Output pipeline YAML file.",
)
@click.option("--name", default="composition", show_default=True, help="Pipeline name.")
def compose(skills: str, output: Path, name: str) -> None:
    """Compose a skill pipeline and save to YAML."""
    skill_ids = [s.strip() for s in skills.split(",") if s.strip()]
    composition = _composer.compose(
        skills=skill_ids,
        pipeline=[{"skill_id": sid, "step": i} for i, sid in enumerate(skill_ids)],
        name=name,
    )
    issues = _composer.validate_composition(composition)
    if issues:
        click.echo("Validation issues:")
        for issue in issues:
            click.echo(f"  - {issue}")

    output.write_text(yaml.dump(composition.model_dump(mode="json"), allow_unicode=True), encoding="utf-8")
    click.echo(f"Pipeline '{name}' saved to {output}.")


@main.command("serve")
@click.option("--port", default=8000, show_default=True, type=int, help="Port to listen on.")
@click.option("--host", default="127.0.0.1", show_default=True, help="Host to bind.")
def serve(port: int, host: str) -> None:
    """Start the skill marketplace API server."""
    try:
        import uvicorn  # type: ignore[import-untyped]
    except ImportError:
        click.echo("uvicorn is required. Install with: pip install uvicorn", err=True)
        sys.exit(1)
    click.echo(f"Starting aumai-skillforge API on http://{host}:{port}")
    uvicorn.run("aumai_skillforge.api:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()

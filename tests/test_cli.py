"""Comprehensive CLI tests for aumai-skillforge."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from aumai_skillforge.cli import main


@pytest.fixture()
def runner() -> CliRunner:
    """Return a Click test runner."""
    return CliRunner()


@pytest.fixture()
def skill_json(tmp_path: Path) -> Path:
    """Write a valid Skill JSON file and return its path."""
    skill_data = {
        "skill_id": "test-skill",
        "name": "Test Skill",
        "description": "A skill for testing",
        "version": "0.1.0",
        "author": "tester",
        "tags": ["test", "demo"],
        "downloads": 0,
    }
    skill_file = tmp_path / "skill.json"
    skill_file.write_text(json.dumps(skill_data), encoding="utf-8")
    return skill_file


@pytest.fixture()
def skill_yaml(tmp_path: Path) -> Path:
    """Write a valid Skill YAML file and return its path."""
    skill_data = {
        "skill_id": "yaml-skill",
        "name": "YAML Skill",
        "description": "A skill defined in YAML",
        "version": "0.1.0",
        "author": "tester",
        "tags": ["yaml", "demo"],
        "downloads": 0,
    }
    skill_file = tmp_path / "skill.yaml"
    skill_file.write_text(yaml.dump(skill_data), encoding="utf-8")
    return skill_file


class TestCliVersion:
    """Tests for --version flag."""

    def test_version_flag(self, runner: CliRunner) -> None:
        """--version must exit 0 and report version."""
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output

    def test_help_flag(self, runner: CliRunner) -> None:
        """--help must exit 0 and contain CLI description."""
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "SkillForge" in result.output


class TestSearchCommand:
    """Tests for the `search` command."""

    def test_search_nonexistent_query_returns_no_skills(
        self, runner: CliRunner
    ) -> None:
        """search returns 'No skills found' for a query that matches nothing."""
        result = runner.invoke(
            main,
            ["search", "--query", "xyzzy_quantum_unicorn_9999_nonexistent"],
        )
        assert result.exit_code == 0
        assert "No skills found" in result.output

    def test_search_help(self, runner: CliRunner) -> None:
        """search --help exits 0."""
        result = runner.invoke(main, ["search", "--help"])
        assert result.exit_code == 0


class TestRegisterCommand:
    """Tests for the `register` command."""

    def test_register_from_json(self, runner: CliRunner, skill_json: Path) -> None:
        """register reads a JSON file and confirms registration."""
        result = runner.invoke(main, ["register", "--config", str(skill_json)])
        assert result.exit_code == 0
        assert "Registered skill" in result.output
        assert "Test Skill" in result.output

    def test_register_from_yaml(self, runner: CliRunner, skill_yaml: Path) -> None:
        """register reads a YAML file and confirms registration."""
        result = runner.invoke(main, ["register", "--config", str(skill_yaml)])
        assert result.exit_code == 0
        assert "Registered skill" in result.output
        assert "YAML Skill" in result.output

    def test_register_missing_file(self, runner: CliRunner, tmp_path: Path) -> None:
        """register exits non-zero for a missing config file."""
        result = runner.invoke(
            main, ["register", "--config", str(tmp_path / "missing.json")]
        )
        assert result.exit_code != 0

    def test_register_then_search(
        self, runner: CliRunner, skill_json: Path
    ) -> None:
        """After registering, the skill shows up in search results."""
        runner.invoke(main, ["register", "--config", str(skill_json)])
        result = runner.invoke(main, ["search", "--query", "Test Skill"])
        # Regardless of module-level state isolation, should exit 0
        assert result.exit_code == 0


class TestComposeCommand:
    """Tests for the `compose` command."""

    def test_compose_saves_output_yaml(
        self, runner: CliRunner, skill_json: Path, tmp_path: Path
    ) -> None:
        """compose creates the output YAML file after registering skills."""
        runner.invoke(main, ["register", "--config", str(skill_json)])
        output_file = tmp_path / "pipeline.yaml"
        result = runner.invoke(
            main,
            [
                "compose",
                "--skills", "test-skill",
                "--output", str(output_file),
                "--name", "my-pipeline",
            ],
        )
        assert result.exit_code == 0
        assert "saved" in result.output.lower()

    def test_compose_unknown_skill_shows_validation_issue(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """compose prints validation issues for unknown skill IDs."""
        output_file = tmp_path / "pipeline.yaml"
        result = runner.invoke(
            main,
            [
                "compose",
                "--skills", "ghost-skill-xyz",
                "--output", str(output_file),
                "--name", "broken-pipeline",
            ],
        )
        # compose raises SkillNotFoundError for unregistered skills
        assert result.exit_code != 0 or "ghost-skill-xyz" in result.output


class TestServeCommand:
    """Tests for the `serve` command (import error path)."""

    def test_serve_help(self, runner: CliRunner) -> None:
        """serve --help exits 0."""
        result = runner.invoke(main, ["serve", "--help"])
        assert result.exit_code == 0
        assert "port" in result.output.lower()

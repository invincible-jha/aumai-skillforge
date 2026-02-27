# Getting Started with aumai-skillforge

This guide takes you from installation to a fully composed, validated skill
pipeline in under ten minutes.

---

## Prerequisites

| Requirement | Minimum version | Notes |
|---|---|---|
| Python | 3.11 | Type hint features used throughout |
| pip | 23.0+ | |
| PyYAML | 6.0+ | Optional — needed for YAML skill files and pipeline export |

No external services, databases, or APIs are required. The registry is fully
in-memory, making SkillForge suitable for unit testing, local development,
and embedding inside larger agent systems.

---

## Installation

```bash
pip install aumai-skillforge
```

With YAML support (recommended):

```bash
pip install aumai-skillforge pyyaml
```

Development install:

```bash
git clone https://github.com/aumai/aumai-skillforge
cd aumai-skillforge
pip install -e ".[dev]"
```

Verify:

```bash
skillforge --version
# aumai-skillforge, version 0.1.0

skillforge --help
# Usage: skillforge [OPTIONS] COMMAND [ARGS]...
#   AumAI SkillForge — Agent skill marketplace and composition CLI.
# Commands:
#   compose   Compose a skill pipeline and save to YAML.
#   register  Register a skill from a config file.
#   search    Search for skills in the registry.
#   serve     Start the SkillForge API server.
```

---

## Step-by-Step Tutorial

### Step 1: Create a skill definition

Skills are defined as JSON or YAML files. Create `web-search.json`:

```json
{
  "skill_id": "web-search-v1",
  "name": "Web Search",
  "description": "Search the web for a given query and return the top results.",
  "version": "0.1.0",
  "author": "aumai-team",
  "tags": ["search", "http", "web"],
  "input_schema": {
    "type": "object",
    "properties": {
      "query": { "type": "string", "description": "The search query." }
    },
    "required": ["query"]
  },
  "output_schema": {
    "type": "object",
    "properties": {
      "results": { "type": "array" },
      "query": { "type": "string" }
    }
  },
  "downloads": 0
}
```

The `input_schema` and `output_schema` follow [JSON Schema](https://json-schema.org/)
conventions. The `required` list in `input_schema` is used by `SkillComposer` for
pipeline validation. The `properties` dict in `output_schema` defines what fields
the skill produces.

---

### Step 2: Register the skill

```bash
skillforge register --config web-search.json
# Registered skill 'Web Search' (ID: web-search-v1).
```

Create a second skill for the pipeline — `summarizer.json`:

```json
{
  "skill_id": "summarizer-v1",
  "name": "Text Summarizer",
  "description": "Summarize a document and return a concise summary.",
  "version": "0.1.0",
  "author": "aumai-team",
  "tags": ["nlp", "summarize", "text"],
  "input_schema": {
    "type": "object",
    "properties": {
      "results": { "type": "array" },
      "query": { "type": "string" }
    },
    "required": ["results", "query"]
  },
  "output_schema": {
    "type": "object",
    "properties": {
      "summary": { "type": "string" }
    }
  },
  "downloads": 0
}
```

```bash
skillforge register --config summarizer.json
# Registered skill 'Text Summarizer' (ID: summarizer-v1).
```

---

### Step 3: Search the registry

```bash
# Search by keyword:
skillforge search --query "web search"
# [web-search-v1] Web Search v0.1.0  relevance=1.00  tags=search,http,web

# Filter by tag:
skillforge search --tags nlp
# [summarizer-v1] Text Summarizer v0.1.0  relevance=1.00  tags=nlp,summarize,text

# List everything:
skillforge search
```

---

### Step 4: Compose a pipeline

Chain the two skills together and save to a YAML file:

```bash
skillforge compose \
  --skills "web-search-v1,summarizer-v1" \
  --name "search-and-summarize" \
  --output pipeline.yaml
```

If the schemas are compatible, you see:

```
Pipeline 'search-and-summarize' saved to pipeline.yaml.
```

If there is a schema mismatch (e.g., `summarizer-v1` requires a field that
`web-search-v1` does not produce), you see:

```
Validation issues:
  - Skill 'web-search-v1' output is missing fields required by 'summarizer-v1': ['results']
Pipeline 'search-and-summarize' saved to pipeline.yaml.
```

The pipeline is still saved so you can inspect it, but the validation issues tell
you exactly which fields need to be added to the upstream skill's `output_schema`.

---

### Step 5: Inspect the generated pipeline YAML

`pipeline.yaml` will look like:

```yaml
description: ''
name: search-and-summarize
pipeline:
- skill_id: web-search-v1
  step: 0
- skill_id: summarizer-v1
  step: 1
skills:
- web-search-v1
- summarizer-v1
```

This is a serialized `SkillComposition` object. You can load it back with Pydantic:

```python
import yaml
from aumai_skillforge.models import SkillComposition

with open("pipeline.yaml", encoding="utf-8") as f:
    data = yaml.safe_load(f)

composition = SkillComposition.model_validate(data)
print(composition.name)    # search-and-summarize
print(composition.skills)  # ['web-search-v1', 'summarizer-v1']
```

---

## Common Patterns and Recipes

### Pattern 1: Build a registry from multiple JSON files

```python
import json
from pathlib import Path
from aumai_skillforge.core import SkillRegistry
from aumai_skillforge.models import Skill

registry = SkillRegistry()
skills_dir = Path("./skills/")

for skill_file in skills_dir.glob("*.json"):
    data = json.loads(skill_file.read_text(encoding="utf-8"))
    skill = Skill.model_validate(data)
    registry.register(skill)
    print(f"Loaded: {skill.skill_id}")
```

### Pattern 2: Search with multi-word query and tag filtering

```python
from aumai_skillforge.core import SkillRegistry

registry = SkillRegistry()
# ... register skills ...

# Find NLP skills that also have "summarize" in their metadata:
results = registry.search(query="summarize text document", tags=["nlp"])
for r in results:
    print(f"{r.skill.skill_id}: {r.relevance:.2f} ({r.skill.downloads} downloads)")
```

### Pattern 3: Validate before executing a pipeline

```python
from aumai_skillforge.core import SkillComposer, SkillRegistry

registry = SkillRegistry()
composer = SkillComposer(registry=registry)
# ... register skills ...

composition = composer.compose(
    skills=["ingest-v1", "clean-v1", "embed-v1"],
    pipeline=[{"skill_id": sid, "step": i} for i, sid in enumerate(["ingest-v1", "clean-v1", "embed-v1"])],
    name="rag-pipeline",
)

issues = composer.validate_composition(composition)
if issues:
    raise RuntimeError(f"Pipeline has schema issues: {issues}")

print("Pipeline is valid. Ready to execute.")
```

### Pattern 4: Track and sort skills by popularity

```python
from aumai_skillforge.core import SkillRegistry

registry = SkillRegistry()
# ... register and use skills ...

# Simulate downloads
for _ in range(10):
    registry.increment_downloads("web-search-v1")
for _ in range(3):
    registry.increment_downloads("summarizer-v1")

# Search returns results sorted by (relevance, downloads):
results = registry.search(query="")  # empty query matches all
for r in results:
    print(f"{r.skill.skill_id}: {r.skill.downloads} downloads")
# web-search-v1: 10 downloads
# summarizer-v1: 3 downloads
```

### Pattern 5: Compose a long multi-step pipeline

```python
from aumai_skillforge.core import SkillComposer, SkillRegistry
from aumai_skillforge.models import Skill

registry = SkillRegistry()

# Register a chain of skills with compatible schemas
steps = [
    ("ingest-v1", ["source"], ["raw_text", "source"]),
    ("clean-v1", ["raw_text"], ["clean_text", "raw_text"]),
    ("chunk-v1", ["clean_text"], ["chunks", "clean_text"]),
    ("embed-v1", ["chunks"], ["embeddings", "chunks"]),
]

for skill_id, required_in, provided_out in steps:
    registry.register(Skill(
        skill_id=skill_id,
        name=skill_id,
        description=f"Step: {skill_id}",
        author="aumai-team",
        input_schema={
            "type": "object",
            "properties": {f: {"type": "string"} for f in required_in},
            "required": required_in,
        },
        output_schema={
            "type": "object",
            "properties": {f: {"type": "string"} for f in provided_out},
        },
    ))

composer = SkillComposer(registry=registry)
skill_ids = [s[0] for s in steps]
composition = composer.compose(
    skills=skill_ids,
    pipeline=[{"skill_id": sid, "step": i} for i, sid in enumerate(skill_ids)],
    name="rag-ingestion-pipeline",
)
issues = composer.validate_composition(composition)
print(f"Issues: {issues}")  # Issues: []
```

---

## Troubleshooting FAQ

**Q: `SkillNotFoundError: 'my-skill-id'`**

The skill has not been registered in the current registry instance. Call
`registry.register(skill)` before calling `registry.get()` or using that
skill ID in a composition. Note that the in-memory registry does not persist
across process restarts — you need to re-register skills each time.

---

**Q: The `compose` command says `SkillNotFoundError` for a skill I just registered.**

The CLI creates a fresh `SkillRegistry()` instance on every invocation. Skills
registered via one `skillforge register` call are not visible to a subsequent
`skillforge compose` call because the process has restarted. Use the Python API
directly when you need to register and compose in the same session.

---

**Q: Validation shows missing fields even though my schemas look correct.**

`validate_composition()` checks `output_schema["properties"]` (a dict) against
`input_schema["required"]` (a list). Make sure:

1. `output_schema` has a `"properties"` key with a dict value.
2. `input_schema` has a `"required"` key with a list value.
3. Every string in `required` appears as a key in `properties`.

The validation is key-name based, not type-based.

---

**Q: `ModuleNotFoundError: No module named 'yaml'`**

Install PyYAML: `pip install pyyaml`. The YAML import is lazy — JSON skill files
do not require PyYAML.

---

**Q: How do I persist skills between sessions?**

Serialize each `Skill` with `skill.model_dump(mode="json")` and write to a JSON
file. On startup, read the files and call `registry.register(Skill.model_validate(data))`.
A future `aumai-registry` integration will handle persistence automatically.

---

**Q: Can two skills have the same `skill_id`?**

Registering a skill with an existing `skill_id` silently replaces the old version.
This is the intended update mechanism. Use versioned IDs (e.g. `web-search-v2`) to
keep both versions available simultaneously.

---

## Next Steps

- Read the [API Reference](api-reference.md) for complete class documentation.
- Explore [examples/quickstart.py](../examples/quickstart.py) for runnable demos.
- Read about [aumai-toolsmith](../../aumai-toolsmith/README.md) to generate skill
  implementations from descriptions.
- Read about [aumai-nanoagent](../../aumai-nanoagent/README.md) to deploy skills
  to edge devices.
- Join the [AumAI Discord](https://discord.gg/aumai) for community support.

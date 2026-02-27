# API Reference — aumai-skillforge

Complete documentation for all public classes, functions, and Pydantic models
in `aumai_skillforge`.

---

## Module: `aumai_skillforge.core`

Public exports: `SkillRegistry`, `SkillComposer`

---

### `class SkillRegistry`

In-memory registry for agent skills. Stores skills keyed by `skill_id`.
All operations are `O(1)` or `O(n)` in the number of registered skills.

```python
from aumai_skillforge.core import SkillRegistry
```

---

#### `SkillRegistry.__init__(self) -> None`

Initialize an empty registry. `_skills` is an empty `dict[str, Skill]`.

---

#### `SkillRegistry.register(skill: Skill) -> None`

Register or update a skill in the registry.

If a skill with the same `skill_id` already exists, it is silently replaced.
This is the intended update mechanism — use versioned IDs (e.g. `search-v2`)
to keep multiple versions simultaneously.

**Parameters:**

| Name | Type | Description |
|---|---|---|
| `skill` | `Skill` | The skill to store. Keyed by `skill.skill_id`. |

**Returns:** `None`

**Example:**

```python
from aumai_skillforge.models import Skill

registry = SkillRegistry()
registry.register(Skill(
    skill_id="summarizer-v1",
    name="Text Summarizer",
    description="Summarize documents.",
    author="aumai-team",
))
```

---

#### `SkillRegistry.search(query: str, tags: list[str] | None = None) -> list[SkillSearchResult]`

Search for skills by query text and optional tag filter.

**Algorithm:**

1. **Tag filtering**: If `tags` is provided, only skills where all tags in the
   list appear in `skill.tags` (case-insensitive) are considered.
2. **Term matching**: The `query` is tokenized into words with `re.findall(r"\w+", ...)`.
   Each term is checked for membership in `skill.name + skill.description + skill.author + skill.tags`
   (all lowercased and joined). The relevance score is `hits / len(query_terms)`, capped at 1.0.
3. **Empty query**: If `query_terms` is empty (blank query), every tag-matching
   skill gets `relevance=1.0`.
4. **Sorting**: Results are sorted descending by `(relevance, skill.downloads)`.
   Skills with equal relevance are ranked by download count.

**Parameters:**

| Name | Type | Default | Description |
|---|---|---|---|
| `query` | `str` | — (required) | Space-separated search terms. Empty string matches all. |
| `tags` | `list[str] \| None` | `None` | If provided, skills must carry all listed tags. |

**Returns:** `list[SkillSearchResult]` — sorted list of matching skills with relevance scores.
Returns an empty list if no skills match.

**Example:**

```python
results = registry.search(query="summarize document", tags=["nlp"])
for r in results:
    print(f"{r.skill.skill_id}: relevance={r.relevance:.2f}")
```

---

#### `SkillRegistry.get(skill_id: str) -> Skill`

Retrieve a skill by its unique identifier.

**Parameters:**

| Name | Type | Description |
|---|---|---|
| `skill_id` | `str` | The unique skill identifier. |

**Returns:** `Skill` — the registered skill.

**Raises:**

- `SkillNotFoundError` — if no skill with the given `skill_id` is registered.
  `SkillNotFoundError` subclasses `KeyError`.

**Example:**

```python
skill = registry.get("summarizer-v1")
print(skill.name)       # Text Summarizer
print(skill.version)    # 0.1.0
```

---

#### `SkillRegistry.increment_downloads(skill_id: str) -> None`

Increment the download counter for a skill.

Uses `Skill.model_copy(update={"downloads": ...})` to create an updated immutable
copy, preserving all other fields. If `skill_id` is not registered, this is a no-op.

**Parameters:**

| Name | Type | Description |
|---|---|---|
| `skill_id` | `str` | The skill identifier to increment. |

**Returns:** `None`

**Example:**

```python
registry.increment_downloads("summarizer-v1")
skill = registry.get("summarizer-v1")
print(skill.downloads)  # 1
```

---

### `class SkillNotFoundError`

```python
class SkillNotFoundError(KeyError):
    ...
```

Raised by `SkillRegistry.get()` and `SkillComposer.compose()` /
`SkillComposer.validate_composition()` when a requested `skill_id` is not in
the registry. Subclasses `KeyError`.

---

### `class SkillComposer`

Compose multiple skills into a sequential pipeline. Depends on a `SkillRegistry`
for skill lookup and schema validation.

```python
from aumai_skillforge.core import SkillComposer
```

---

#### `SkillComposer.__init__(self, registry: SkillRegistry) -> None`

**Parameters:**

| Name | Type | Description |
|---|---|---|
| `registry` | `SkillRegistry` | The registry to use for skill lookups. |

---

#### `SkillComposer.compose(skills: list[str], pipeline: list[dict[str, object]], name: str = "composed-pipeline", description: str = "") -> SkillComposition`

Chain skills into a named pipeline composition.

Validates that every `skill_id` in `skills` exists in the registry before
creating the composition. Does not validate schema compatibility — call
`validate_composition()` for that.

**Parameters:**

| Name | Type | Default | Description |
|---|---|---|---|
| `skills` | `list[str]` | — (required) | Ordered list of `skill_id` strings. |
| `pipeline` | `list[dict[str, object]]` | — (required) | Step-by-step config for each skill connection. |
| `name` | `str` | `"composed-pipeline"` | Human-readable pipeline name. |
| `description` | `str` | `""` | Optional description of the pipeline's purpose. |

**Returns:** `SkillComposition` — the composed pipeline.

**Raises:**

- `SkillNotFoundError` — if any `skill_id` in `skills` is not registered.

**Example:**

```python
from aumai_skillforge.core import SkillComposer, SkillRegistry
from aumai_skillforge.models import Skill

registry = SkillRegistry()
registry.register(Skill(skill_id="step-a", name="A", description="", author="me"))
registry.register(Skill(skill_id="step-b", name="B", description="", author="me"))

composer = SkillComposer(registry=registry)
composition = composer.compose(
    skills=["step-a", "step-b"],
    pipeline=[{"skill_id": "step-a", "step": 0}, {"skill_id": "step-b", "step": 1}],
    name="my-pipeline",
)
print(composition.name)    # my-pipeline
print(composition.skills)  # ['step-a', 'step-b']
```

---

#### `SkillComposer.validate_composition(composition: SkillComposition) -> list[str]`

Check schema compatibility between consecutive skills in a pipeline.

For each consecutive pair `(current, next)` in the pipeline:

1. Extract `current.output_schema.get("properties", {})` → set of output field names.
2. Extract `next.input_schema.get("required", [])` → set of required input fields.
3. If the required set is not a subset of the output properties, record an issue.

**Parameters:**

| Name | Type | Description |
|---|---|---|
| `composition` | `SkillComposition` | The pipeline to validate. |

**Returns:** `list[str]` — list of validation issue strings. An empty list means the
pipeline is schema-compatible. Issues are human-readable sentences describing which
skill is missing which fields.

**Special cases:**

- Empty `skills` list → single issue: `"Composition has no skills."`.
- Any unregistered `skill_id` → issue per missing skill; schema check is skipped.

**Example:**

```python
issues = composer.validate_composition(composition)
if not issues:
    print("Pipeline is valid.")
else:
    for issue in issues:
        print(f"  Issue: {issue}")
# Issue: Skill 'step-a' output is missing fields required by 'step-b': ['result']
```

---

## Module: `aumai_skillforge.models`

Public exports: `Skill`, `SkillComposition`, `SkillSearchResult`

All models use Pydantic v2 (`BaseModel`).

---

### `class Skill`

A composable agent skill in the marketplace. This is the core unit of the
SkillForge system.

```python
from aumai_skillforge.models import Skill
```

**Fields:**

| Field | Type | Default | Constraints | Description |
|---|---|---|---|---|
| `skill_id` | `str` | — (required) | — | Unique identifier. Used as registry key. |
| `name` | `str` | — (required) | — | Human-readable display name. |
| `description` | `str` | — (required) | — | What the skill does. Used in relevance search. |
| `version` | `str` | `"0.1.0"` | — | Semantic version string. |
| `author` | `str` | — (required) | — | Author name or organization. Used in relevance search. |
| `input_schema` | `dict[str, object]` | `{}` | — | JSON Schema describing the skill's inputs. |
| `output_schema` | `dict[str, object]` | `{}` | — | JSON Schema describing the skill's outputs. |
| `tags` | `list[str]` | `[]` | — | Searchable tag strings. Used in tag filtering and relevance search. |
| `downloads` | `int` | `0` | `>= 0` | Download counter. Used for popularity sorting. |

**JSON Schema conventions for `input_schema` and `output_schema`:**

SkillComposer reads two specific keys during pipeline validation:

- `output_schema["properties"]` — `dict` of field names the skill produces.
- `input_schema["required"]` — `list` of field names the skill needs as input.

Recommended structure:

```python
input_schema = {
    "type": "object",
    "properties": {
        "query": {"type": "string", "description": "The search query."}
    },
    "required": ["query"],
}
output_schema = {
    "type": "object",
    "properties": {
        "results": {"type": "array"},
        "query": {"type": "string"},
    },
}
```

**Full example:**

```python
skill = Skill(
    skill_id="web-search-v1",
    name="Web Search",
    description="Search the web for a given query.",
    version="0.1.0",
    author="aumai-team",
    tags=["search", "http", "web"],
    input_schema={
        "type": "object",
        "properties": {"query": {"type": "string"}},
        "required": ["query"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "results": {"type": "array"},
            "query": {"type": "string"},
        },
    },
    downloads=0,
)
```

---

### `class SkillComposition`

A named pipeline composed of multiple skills in sequential order.

```python
from aumai_skillforge.models import SkillComposition
```

**Fields:**

| Field | Type | Default | Description |
|---|---|---|---|
| `name` | `str` | — (required) | Human-readable pipeline name. |
| `skills` | `list[str]` | — (required) | Ordered list of `skill_id` strings. |
| `pipeline` | `list[dict[str, object]]` | `[]` | Step-by-step pipeline configuration (e.g. `{"skill_id": "...", "step": 0}`). |
| `description` | `str` | `""` | Optional description. |

**Serialization example:**

```python
import yaml

composition = SkillComposition(
    name="search-and-summarize",
    skills=["web-search-v1", "summarizer-v1"],
    pipeline=[
        {"skill_id": "web-search-v1", "step": 0},
        {"skill_id": "summarizer-v1", "step": 1},
    ],
)
print(yaml.dump(composition.model_dump(mode="json"), allow_unicode=True))
```

**Deserialization example:**

```python
import yaml
from aumai_skillforge.models import SkillComposition

with open("pipeline.yaml", encoding="utf-8") as f:
    data = yaml.safe_load(f)
composition = SkillComposition.model_validate(data)
```

---

### `class SkillSearchResult`

A search result pairing a skill with its computed relevance score.

```python
from aumai_skillforge.models import SkillSearchResult
```

**Fields:**

| Field | Type | Default | Constraints | Description |
|---|---|---|---|---|
| `skill` | `Skill` | — (required) | — | The matched skill. |
| `relevance` | `float` | — (required) | `0.0 <= relevance <= 1.0` | Relevance score. 1.0 means all query terms matched. |

**Example:**

```python
results = registry.search(query="search web")
for r in results:
    print(f"{r.skill.skill_id}: {r.relevance:.3f} (downloads: {r.skill.downloads})")
```

---

## Module: `aumai_skillforge.cli`

The CLI is accessed via the `skillforge` command installed by the package.
All commands are built with [Click](https://click.palletsprojects.com/).

| Command | Description |
|---|---|
| `skillforge search` | Search for skills by query and optional tags. |
| `skillforge register --config PATH` | Register a skill from a YAML or JSON file. |
| `skillforge compose --skills IDS --output PATH` | Compose a pipeline from skill IDs and save to YAML. |
| `skillforge serve` | Start the API server (not yet implemented). |

**Note on CLI state:** The CLI creates a fresh `SkillRegistry()` and `SkillComposer()`
on every invocation. Skills registered in one call are not persisted for subsequent
calls. Use the Python API directly when you need to register and compose in a single
session.

See the [README](../README.md) for full CLI usage examples with sample output.

---

## Package metadata

```python
import aumai_skillforge
print(aumai_skillforge.__version__)  # "0.1.0"
```

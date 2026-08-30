<!-- capsule-v2 -->
# Checkpoint version migration — how do old checkpoint files load into a newer runtime without data loss or silent misvalidation?

**Source:** crewAI MIT `main@9e9a8577becc322f98a966ad88d7904251049744`; Codebase Memory `ext-crewAI`. **Question:** Where do discriminator backfills live so legacy snapshots validate against current models?

## Version-gated wrap-validator migrations
**Path/Symbol:** `lib/crewai/src/crewai/state/runtime.py` (`RuntimeState._deserialize` :200–214, `_migrate` :89–126, `_backfill_discriminators` :169–176 and friends :127–168; serializer :192–199).
**Signature:** `_migrate(data: dict[str, Any]) -> dict[str, Any]` applied inside a `model_validator(mode="wrap")`.
**Data Shape:** envelope `{"crewai_version", "parent_id", "branch", "entities": [...], "event_record": {...}}`; migration threshold `Version("1.14.6")`.

### Decisive source
```python
@model_validator(mode="wrap")
@classmethod
def _deserialize(cls, data, handler):
    if isinstance(data, dict) and "entities" in data:
        data = _migrate(data)
        record_data = data.get("event_record")
        state = handler(data["entities"])
        ...
        state._parent_id = data.get("parent_id")
        state._branch = data.get("branch", "main")
        return state
    return handler(data)
```
```python
def _backfill_memory_kind(value):
    """Infer ``memory_kind`` from structural fields on legacy memory dicts."""
    if not isinstance(value, dict) or "memory_kind" in value:
        return
    if "scopes" in value:      value["memory_kind"] = "slice"
    elif "root_path" in value: value["memory_kind"] = "scope"
    else:                      value["memory_kind"] = "memory"
```

**Flow:** raw JSON → wrap validator sees the entity-envelope shape → `_migrate` reads `crewai_version` (missing ⇒ warn + treat as 0.0.0) → each version block transforms forward in order so migrations compose → THEN the normal pydantic pipeline validates the migrated payload → private lineage fields restored from envelope.
**Invariant:** Migrations run BEFORE validation because backfilled discriminators are required for model_validate to succeed — validating first would raise on legacy data. Structural inference only when safe: memory kind from field shapes; knowledge sources backfilled ONLY for plain-string content, everything else left to fail loudly with an upgrade instruction. Blocks are additive per release — porting one block means anchoring its exact threshold version.
**Probe:** `.venv/bin/python -m pytest "lib/crewai/tests/test_checkpoint.py::TestFlowInitialStateSerialization" -q` (expect 4 passed incl. class-ref round-trip); static anchor: `grep -c 'stored < Version("1.14.6")' lib/crewai/src/crewai/state/runtime.py` → 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-crewAI", query: "_migrate checkpoint version backfill discriminators deserialize", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt migrate-inside-wrap-validator with structural-only inference and loud refusal otherwise; adapt thresholds to your own release history; omit event-record persistence if you don't replay. Direct tests executed green at pin.

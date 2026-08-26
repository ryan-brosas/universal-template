<!-- capsule-v2 -->
# Versioned snapshot contract — durable, validated, loudly-rejected-on-unknown

**Source:** OpenAI Agents Python MIT `main@cb8a2e7e7dd83a427cff9076e58356d00c4f90b2`; Codebase Memory `openai-agents-python`. **Question:** How is serialized run state made a versioned contract that survives schema evolution?

## The versioned contract
**Path/Symbol:** `src/agents/run_state.py:SCHEMA_VERSION_SUMMARIES` (:186-212), version stamp (:1779), read validation (:2200-2206, :3838-3857, :3900-3917).
**Signature:** `RunState.to_json()` / `from_string()` / `from_json()`; `SCHEMA_VERSION_SUMMARIES: dict[str, str]`.
**Data Shape:** every serialized blob is stamped `$schemaVersion` at write (:1779) and validated BEFORE anything else touches it on read (:2200-2206).

### Decisive source
```python
SCHEMA_VERSION_SUMMARIES: dict[str, str] = {
    "1.0": "Initial RunState snapshot format for HITL pause/resume flows.",
    ...
    "1.6": "Persists explicit approval rejection messages across resume flows.",
    "1.15": "Persists canonical tool invocation identity plus sanitized mount authority ...",
    "1.16": "Lets an exact call approval decision override a sticky decision for the same tool.",
}
# Unknown versions fail LOUDLY: "Run state schema version is not supported. Supported versions are: …" (:3838-3857)
```

**Flow:** The version list doubles as the changelog — each bump is recorded in prose. Features gate by minimum parsed `(major, minor)` tuples — Programmatic Tool Calling data below 1.13 is rejected with a named error (:~3900-3917); older blobs degrade gracefully (tool_invocations rebuilt only ≥1.15, else a legacy-reconstruction flag is set).
**Invariant:** Treat persisted agent state as a versioned contract — stamp every write, keep the version list as the changelog, gate features by minimum tuples, refuse unknown versions loudly.
**Probe:** `tests/test_run_state.py:830-853` (missing/invalid version), :8550-8552 (parametrized future versions), :9016-9018 (feature-below-minimum).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openai-agents-python", query: "SCHEMA_VERSION_SUMMARIES schema version RunState", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt stamp-every-write + version-list-as-changelog + minimum-tuple gating + loud unknown-version refusal; adapt the specific version numbers; omit provider-specific feature gates. Direct tests pin all four behaviors.

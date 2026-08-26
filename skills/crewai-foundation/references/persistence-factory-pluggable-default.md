<!-- capsule-v2 -->
# Persistence factory pluggable default — how does an application redirect ALL flow state persistence without touching every @persist site?

**Source:** crewAI MIT `main@9e9a8577becc322f98a966ad88d7904251049744`; Codebase Memory `ext-crewAI`. **Question:** What makes a process-wide default safe when the factory may be invoked multiple times per flow?

## Late-resolving global factory + shared-durable-state contract
**Path/Symbol:** `lib/crewai/src/crewai/flow/persistence/factory.py` (`set_flow_persistence_factory` :31–45, `default_flow_persistence` :48–60); registry twin `base.py:26–58` (`_persistence_registry`, `__init_subclass__` auto-registration).
**Signature:** `set_flow_persistence_factory(factory: FlowPersistenceFactory | None) -> None`; `default_flow_persistence() -> FlowPersistence`.
**Data Shape:** module global `_factory: FlowPersistenceFactory | None`; concrete subclasses self-register under their class NAME.

### Decisive source
```python
def set_flow_persistence_factory(factory):
    """...The default is resolved at each fall-back site (``@persist`` and the
    runtime's pause/resume paths), so the factory may be called more than once
    for a single flow. Return instances backed by shared durable state (or a
    singleton) so state saved on one call is visible to the next -- the
    built-in SQLite default satisfies this by sharing one on-disk file.
    """
    global _factory
    _factory = factory


def default_flow_persistence():
    factory = _factory
    if factory is not None:
        return factory()
    from crewai.flow.persistence.sqlite import SQLiteFlowPersistence

    return SQLiteFlowPersistence()
```

**Flow:** startup calls the setter once (None restores SQLite) → every fallback site — decorator default, pause auto-persist, resume, fork — resolves the CURRENT factory at call time → instances may be fresh objects per call provided they share durable backing (file/db). Parallel registry: any concrete FlowPersistence subclass is recorded by name for dict-based reconstruction (`_resolve_persistence` reads `persistence_type`).
**Invariant:** Late resolution (not captured-at-import) is what lets tests swap factories AFTER flows are defined; the documented multi-call contract forbids stateful-per-instance defaults like in-memory dicts. Import of SQLite is deferred INSIDE the function to keep it optional and avoid cycles.
**Probe:** `.venv/bin/python -m pytest lib/crewai/tests/test_flow_persistence_factory.py -q` (expect 3 passed); static anchors: `global _factory` ×1 :44, `_persistence_registry[cls.__name__] = cls` ×1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-crewAI", query: "set_flow_persistence_factory default_flow_persistence registry subclass", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt late-resolving setter + documented instance-sharing contract + name registry; adapt to DI containers if your app has one; omit the registry if you never reconstruct backends from serialized definitions. Direct tests executed green at pin.

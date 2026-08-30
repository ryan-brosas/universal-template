<!-- capsule-v2 -->
# Persist backend resolution precedence — which of instance persistence, method @persist, class @persist, or the process factory wins?

**Source:** crewAI MIT `main@9e9a8577becc322f98a966ad88d7904251049744`; Codebase Memory `ext-crewAI`. **Question:** When several persistence configurations coexist, what is the resolution order and why is it cached by definition identity?

## Definition-scoped backend cache
**Path/Symbol:** `lib/crewai/src/crewai/flow/runtime/__init__.py` (`Flow._persist_method_completion` :2988–3011, `_persist_backend_for` :3013–3020, `_resolve_persist_backend` :3022–3036, `_persist_backends` :755–757); decorator stamper `lib/crewai/src/crewai/flow/persistence/decorators.py:147–191`; pluggable default `factory.py:31–60`.
**Signature:** `_persist_method_completion(self, method_name: FlowMethodName) -> None`.
**Data Shape:** `_persist_backends: dict[int, FlowPersistence]` keyed by `id(persist_definition)`; `_instance_persistence: bool` marks engine-derived (not user-supplied) backends.

### Decisive source
```python
persist_definition = (
    method_definition.persist
    if method_definition.persist is not None
    else self._definition.persist
)
if persist_definition is None or not persist_definition.enabled:
    return

# An instance-supplied backend overrides definition backends; one the
# engine derived from the flow-level definition must not shadow a
# method-scoped persist config.
backend = (
    self.persistence
    if self._instance_persistence and self.persistence is not None
    else self._persist_backend_for(persist_definition)
)
```

**Flow:** per completed method resolve the effective definition (method-level beats flow-level; both honor `enabled=False` as kill switch) → choose backend: user-passed `persistence=` instance wins outright, else derive from the definition → derivation cached under `id(persist_definition)` so ONE shared backend object serves all methods of that scope → save via static `PersistenceDecorator.persist_state`, which requires `state.id` (`if not flow_uuid:` raise) and wraps backend failures in `RuntimeError("State persistence failed: ...")` (:132).
**Invariant:** The cache key is the DEFINITION OBJECT, not the method name — two methods sharing a class-level config share one backend instance; a method override gets its own. Engine-derived backends must never shadow an explicit instance (`_instance_persistence` flag). Saves run via `await asyncio.to_thread(self._persist_method_completion, ...)` (:2940) so blocking I/O never stalls the loop.
**Probe:** `.venv/bin/python -m pytest lib/crewai/tests/test_flow_persistence_factory.py -q` (expect 3 passed: registered-factory default, sqlite fallback, falsy-persistence honoring).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-crewAI", query: "_persist_backend_for instance persistence definition enabled factory", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the four-tier precedence (instance > method def > flow def > factory/SQLite) with definition-identity caching; adapt the id()-keyed cache to weakrefs if definitions are created dynamically; omit the enabled kill-switch at your peril. Direct tests executed green at pin.

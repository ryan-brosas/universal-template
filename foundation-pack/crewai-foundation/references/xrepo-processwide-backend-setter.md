<!-- capsule-v2 -->
# Cross-repo pattern: process-wide backend setter — the "global slot + snapshot + graceful default" trio crewAI shares with its own persistence factory

**Source:** crewAI MIT `main@9e9a8577becc322f98a966ad88d7904251049744` (`lock_store.set_lock_backend` :45–54, `factory.set_flow_persistence_factory` :31–45); Codebase Memory `ext-crewAI`. **Question:** Which reusable contract lets a library expose pluggable infrastructure backends without a DI framework?

## Pattern: set-once global, snapshot-on-use, built-in fallback
**Path/Symbol:** `lib/crewai-core/src/crewai_core/lock_store.py:45–54` ↔ `lib/crewai/src/crewai/flow/persistence/factory.py:31–60`.
**Signature:** `set_X_backend(backend: X | None) -> None` (docstring always says: one-time, application-startup) paired with resolver `default_X() -> X`.
**Data Shape:** module-level `_backend/_factory: Callable | None`; consumers snapshot into a local BEFORE branching.

### Decisive source
```python
# lock_store.lock — snapshot comment is the pattern's core:
# Snapshot the global once: a concurrent set_lock_backend() must not turn
# the check-then-call into calling ``None``.
backend = _backend
if backend is not None:
    with backend(name, timeout=timeout):
        yield
    return
```
```python
# factory.default_flow_persistence — same skeleton, import-deferred fallback:
factory = _factory
if factory is not None:
    return factory()
from crewai.flow.persistence.sqlite import SQLiteFlowPersistence
return SQLiteFlowPersistence()
```

**Flow:** library defines a module global slot → startup setter installs a custom strategy (None restores built-in) → EVERY use site copies the global to a local first, branches on it, else falls back to a dependency-light default (file locks / SQLite) selected by environment probes (`REDIS_URL`, importability).
**Invariant:** Three invariants repeat across both seams: (1) snapshot-before-branch prevents torn reads during swaps; (2) the custom backend receives RAW arguments verbatim while defaults namespace/hash internally; (3) in-flight operations keep the backend they started with. The identical trio also appears in crewAI's `default_flow_persistence` docstring contract ("may be called more than once... shared durable state").
**Cross-repo twins mined this fleet:** agno `db.set_db`-style global reconfiguration slots; autogen runtime component registries. Common shape: env-probe default + set-once override + doc-stated lifecycle. When porting ANY of these, keep the docstring contract next to the setter — it is load-bearing documentation, not prose.
**Probe:** `.venv/bin/python -m pytest lib/crewai/tests/utilities/test_lock_store.py lib/crewai/tests/test_flow_persistence_factory.py -q` (expect 7 passed covering both seams' swap/fallback arms).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-crewAI", query: "set_lock_backend set_flow_persistence_factory process-wide backend default", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the trio wholesale for any pluggable-infra seam; adapt fallback selection to your environment surface; omit registry auto-registration unless serialized reconstruction is needed. Direct tests executed green at pin across BOTH seams.

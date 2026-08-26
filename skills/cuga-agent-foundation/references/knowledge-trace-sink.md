<!-- capsule-v2 -->
# Opt-in JSONL retrieval trace sink — how do you add per-query observability to a search path with zero cost and zero PII risk when off?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** You want append-only JSONL query traces (expansion decisions, fusion ranks, rerank deltas) from a production search path — how do you make it fully-off by default, thread-safe, and crash-proof?

## Default OFF; env-var OR context-manager activation; every failure swallowed
**Path/Symbol:** `src/cuga/backend/knowledge/trace.py` — module docstring :1-24, `TRACE_SCHEMA_VERSION = 1` :41, `_TraceSink` singleton :44-118 (`_lock`, `_path`, `_enabled`, `_override_path/_override_enabled`), `emit` :126-132 + `_TraceSink.emit` :83-110, `is_enabled` :135-141, `capture_trace` :145-159, `reset_for_tests` :162-169.
**Signature:** `emit(record: dict) -> None`; `is_enabled() -> bool`; `capture_trace(path) -> ContextManager[Path]`; activation = BOTH `KNOWLEDGE_TRACE=1` AND `KNOWLEDGE_TRACE_FILE=<path>` set, OR inside `capture_trace`.
**Data Shape:** one JSON object per line; `_schema_version` injected via `setdefault` when absent; readers must refuse records with a higher schema version than they understand.

### Decisive source
```python
# :62-81 override beats env; env re-read EVERY call so tests can patch os.environ mid-test
if self._override_enabled: return self._override_path
if not self._enabled:
    if os.environ.get("KNOWLEDGE_TRACE") == "1":
        env_path = os.environ.get("KNOWLEDGE_TRACE_FILE")
        if env_path: self._enabled = True; self._path = Path(env_path); return self._path
    return None
```
```python
# :97-110 serialize OUTSIDE the lock, IOErrors logged-and-dropped — a failing
# trace must never crash the production search path
try: line = json.dumps(record, ensure_ascii=False)
except (TypeError, ValueError): logger.warning(...); return
with self._lock:
    try: ... path.open("a", ...) ...
    except OSError as exc: logger.warning(f"trace write failed for {path}: {exc}")
```
**Flow:** caller builds record only if `is_enabled()` (cheap hot-path guard) → emit → resolve active path (override > env; lazy re-read each call) → defensive copy + version stamp → serialize → single module lock serializes appends across concurrent searches → mkdir parents on first write (a block that never emits leaves NO file).
**Invariant:** (1) Disabled path is ONE bool/dict check — no record building. (2) The context-manager override BEATS env vars so a developer's exported `KNOWLEDGE_TRACE` can't pollute test runs. (3) Never raise from emit: serialization and IO failures log once and drop. (4) PII discipline: sink path defaults None, nothing on stdout/stderr, operators opt in per run. (5) File created lazily on first EMIT, not on enter.

**Probe:** No direct unit suite at HEAD for trace.py itself (coverage caveat — source-read verified); consumers are pinned indirectly via engine search-with-stats paths. The module ships its own contract in docstrings + `__main__`-style usage by pipeline stages 04/05.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "emit capture_trace trace sink JSONL KNOWLEDGE_TRACE", limit: 8 });
```
## Verdict
Adopt this exact shape for opt-in structured tracing of any hot path: default-off singleton, dual activation, swallow-all failures, schema-version stamping. Adapt the env names. Omit the override layer only if you have no test/CLI need for per-block scoping.

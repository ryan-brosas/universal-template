<!-- capsule-v2 -->
# Check registry plugin kernel — how do third-party GEO checks plug in without ever breaking an audit?

**Source:** GeoReady (Geo Optimizer) MIT `main@a7165be2`; Codebase Memory `ext-aeo-geo-optimizer-skill`. **Question:** How does a plugin check register, run, and fail without corrupting scores or other plugins?

## Thread-safe class-level registry over a duck-typed Protocol
**Path/Symbol:** `src/geo_optimizer/core/registry.py:CheckRegistry` (60–210).
**Signature:** `register(check)`, `unregister(name)`, `get(name) -> AuditCheck | None`, `all() -> list`, `names() -> list[str]`, `clear()`, `load_entry_points() -> int`, `run_all(url, soup=None, **kwargs) -> list[CheckResult]`.
**Data Shape:** `CheckResult(name, score=0, max_score=10, passed=False, details={}, message="")`. Checks satisfy `AuditCheck` Protocol (`name`/`description`/`max_score` attrs + `run(url, soup=None, **kwargs) -> CheckResult`) — runtime_checkable so `isinstance` validates shape, not inheritance.

### Decisive source
```python
@classmethod
def load_entry_points(cls) -> int:
    with cls._lock:
        if cls._loaded_entry_points:
            return 0
        cls._loaded_entry_points = True   # set BEFORE loading: concurrent callers get 0, not double-load
        ...
        for ep in eps:
            try:
                check_class = ep.load()
                check = check_class() if isinstance(check_class, type) else check_class
                if not isinstance(check, AuditCheck): logger.warning(...); continue   # warn-and-skip, NOT raise
                if check.name in cls._checks: logger.warning(...); continue          # dup plugin skipped
                cls._checks[check.name] = check    # direct insert: register() would deadlock on held lock
                loaded += 1
            except Exception as exc:
                logger.warning("Plugin '%s' failed to load: %s", ep.name, exc)       # fix #202: never blocks audit
```

**Flow:** entry-point group `geo_optimizer.checks` discovered lazily on first `_build_audit_result` call (`CheckRegistry.load_entry_points()` at audit.py:600) → each plugin instantiated-if-class → protocol-validated → inserted under the already-held lock → later `run_all` snapshots checks under lock, then iterates WITHOUT the lock giving each plugin a `copy.deepcopy(soup)` so mutation can't leak between plugins (fix #55); any plugin exception is converted into a zero-score `CheckResult(message=f"Error in check: {e}")` — never propagated.
**Invariant:** Plugin results land in `AuditResult.extra_checks` and NEVER touch the base 0–100 score; duplicate names raise `ValueError` only for manual `register()` but are silently skipped during entry-point load; failed plugins degrade to log warnings. A porter who lets one bad plugin raise kills every audit — the whole design point is fail-isolated extensibility.
**Probe:** `tests/test_registry.py::test_run_all_check_fallito_non_blocca_altri` (a raising check yields score-0 result while others still run; also `test_register_check_duplicato_solleva_errore`, `test_run_all_passa_kwargs_al_check`).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-geo-optimizer-skill", query: "CheckRegistry load_entry_points plugin", limit: 5, fields: ["signature","name","file"] });
```

## Verdict
Adopt the Protocol + snapshot-under-lock + deepcopy-soup + exception-to-zero-score pattern verbatim for any user-extensible checker; adapt the entry-point group name and `CheckResult` fields; omit the Python 3.9 `entry_points()` compat ladder if your floor is ≥3.10.

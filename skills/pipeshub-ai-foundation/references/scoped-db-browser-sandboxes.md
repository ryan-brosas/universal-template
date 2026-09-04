<!-- capsule-v2 -->
# Scoped DB + browser sandboxes — what policy shape do read-only SQL and shared-page web tools take?

**Source:** pipeshub-ai Apache-2.0 `main@4a02110dd9a7a644d8ba7a5ccd295c58a3c3628f`; Codebase Memory `pipeshub-ai`. **Question:** How do the two Phase-3 taxonomy sandboxes (SQL, browser) enforce their minimal policies with zero extra dependencies?

## Keyword-scan table allowlist over stdlib sqlite3; lazy single Chromium page
**Path/Symbol:** `backend/python/app/agent_loop_lib/sandbox/db_sandbox.py:SqliteDBSandbox._check_policy/_execute_sync` (L55–82); `backend/python/app/agent_loop_lib/sandbox/browser_sandbox.py:PlaywrightBrowserSandbox._ensure_page` (L31–44).
**Signature:** `async def query(sql, params=None) -> list[dict]` (policy check BEFORE thread offload; `cursor.description is None` ⇒ write path returns `[{"rows_affected": n}]` after commit); `_ensure_page() -> Page` (one browser+page shared until `close()`).
**Data Shape:** `mode: "readonly" | "readwrite"`; `table_allowlist: list[str] | None`; `_TABLE_NAME_RE` captures tables after `from|join|into|update` incl. quote-char forms. Browser errors are `BrowserSandboxError` (lazy playwright import w/ install hint).

### Decisive source
```python
stripped = sql.strip().lower()
first_word = stripped.split(None, 1)[0] if stripped else ""
if self._mode == "readonly" and first_word != "select":
    raise DBSandboxError(f"DB sandbox is readonly — statement type {first_word!r} is not allowed")
if self._table_allowlist is not None:
    referenced = {m.group(2).lower() for m in _TABLE_NAME_RE.finditer(sql)}
    disallowed = referenced - allowed
    if disallowed:
        raise DBSandboxError(f"Query references table(s) outside the allowlist: {sorted(disallowed)}")

# docstring honesty clause a porter MUST keep:
"""Table detection is a best-effort keyword scan (not a full SQL parser) —
sufficient to prevent ACCIDENTAL cross-table access from agent-authored
queries, not adversarial SQL written to evade it; pair with least-privilege
DB file permissions for real defense in depth."""
```

**Flow:** query → mode gate (top-level SELECT only in readonly) → allowlist set-difference → `asyncio.to_thread(sqlite3)` → Row-dict rows or rows_affected marker. Browser: first tool call lazily starts headless Chromium + one page; navigate/get_text/click/fill/screenshot all share it; async-CM closes deterministically.
**Invariant:** (1) The scan is explicitly NOT adversarial-proof — porters who present it as hard isolation lie; pair with filesystem permissions. (2) Policy checks run before the executor offload and raise typed sandbox errors (data-shape failures stay data per the backend contract — these are POLICY violations, so raising is correct). (3) One shared page per sandbox instance is the whole resource model; no per-call browser churn.
**Probe:** No direct unit suites for either sandbox at HEAD (`SqliteDBSandbox`/`PlaywrightBrowserSandbox` absent from tests/) — coverage caveat recorded; deterministic probes: symbol greps + retrieval of both classes.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pipeshub-ai", query: "SqliteDBSandbox PlaywrightBrowserSandbox _check_policy _TABLE_NAME_RE", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the honest-policy pattern (typed gates + documented adversarial limits); adapt to real SQL parsers or Postgres backends if your threat model needs them. Omit PipesHub's duck-typed-future-backend notes. Coverage caveat: no direct tests upstream — verify on-target before trusting behavior.

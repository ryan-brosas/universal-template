<!-- capsule-v2 -->
# Config-store version duality — how does one table serve an UPSERTed working draft and append-only numbered published versions without either corrupting the other?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-cuga-agent`. **Question:** How do you model draft-vs-published agent config lifecycle in a single relational table so "latest" never means the draft, and sync bootstrap code can call async storage from inside a running loop?

## `agent_configs` PK (tenant, instance, agent, version) with 'draft' as a magic row
**Path/Symbol:** `src/cuga/backend/server/config_store.py` — `run_sync` 46–60, `_ensure_schema` 114–147, `save_config` 168–195, `load_config` 221–247, `get_latest_version` 273–291, `save_draft` 294–311, `load_draft` 314–327; merge helper `src/cuga/backend/server/managed_mcp.py:_merge_existing_mcp_servers` 104–134; direct tests `tests/unit/test_preserve_configs_on_startup.py`, `tests/unit/test_manage_publish_sync.py`.
**Signature:** `save_config(config, agent_id) -> str` (returns the new version string); `load_config(version: str|None, agent_id) -> (config|None, version|None)` — None means latest PUBLISHED; `save_draft/load_draft` target the `'draft'` row.
**Data Shape:** rows are `(tenant_id, instance_id, agent_id, version, config_json TEXT, created_at, updated_at)`; versions are decimal STRINGS ('1','2',…) sorted by `CAST(version AS INTEGER)`; `'--draft'` twin suffixes are parsed away by `_parse_agent_id`.

### Decisive source
```python
# config_store.py:302-308 — draft is ONE row: upsert on conflict
INSERT INTO agent_configs (..., 'draft', ...)
ON CONFLICT(tenant_id, instance_id, agent_id, version)
DO UPDATE SET config_json = excluded.config_json, updated_at = excluded.updated_at
```
```python
# config_store.py:174-181 + 188-192 — published versions APPEND at MAX+1
SELECT MAX(CAST(version AS INTEGER)) as max_ver ... WHERE ... AND version != 'draft'
...
next_version = (max_ver or 0) + 1
```
```python
# config_store.py:238-239 — "latest" excludes the draft explicitly
WHERE ... AND version != 'draft'
ORDER BY CAST(version AS INTEGER) DESC LIMIT 1
```
```python
# config_store.py:55-60 — run_sync bridges sync callers in BOTH loop contexts
try:
    asyncio.get_running_loop()
except RuntimeError:
    return asyncio.run(coro)
with ThreadPoolExecutor(max_workers=1) as pool:
    return pool.submit(asyncio.run, coro).result()
```

**Flow:** manage UI PATCHes write the draft row (UPSERT); Publish calls `save_config`, which numbers a fresh append-only row `MAX(CAST(version AS INTEGER))+1`; every read of "current" config (`load_config(None)`) selects latest published EXCLUDING draft. Manager-mode startup replays that latest published config into runtime (tools → managed MCP YAML → policies → registry reload). The managed-MCP write path merge-fills `command/args/transport/env/cwd/description` FROM THE EXISTING YAML when a new entry lacks `command` (`managed_mcp.py:115-120`) so partial manage-UI edits never drop launch details; `ensure_managed_mcp_file_exists` strips legacy `filesystem` MCP entries (now runtime tools).
**Invariant:** the `!= 'draft'` exclusion appears in EVERY published-read path (`load_config(None)`, `get_latest_version`, `list_versions`, `save_config`'s MAX scan) — one missed filter would let the draft shadow published versions or corrupt numbering. And `run_sync` must detect a running loop BEFORE `asyncio.run`: calling `asyncio.run` inside a live loop raises; a private single-worker thread running its own loop keeps both worlds alive.
**Probe:** executed against the repo venv — reset DB, double `save_draft` then assert `load_draft == {'v': 2}` (upserted, not appended), `save_config` twice asserting versions `'1'`,`'2'`, `load_config(None)` returns version `'2'`, `len(list_versions()) == 2` → printed `OK: draft=UPSERT singleton vs published=append-only MAX+1 confirmed`.
**Executed:** upstream suites also green this pass — `tests/unit/test_preserve_configs_on_startup.py` → **8 passed** (incl. `test_run_sync_works_when_event_loop_already_running`, preserve-ladder cases), `tests/unit/test_manage_publish_sync.py::test_publish_syncs_draft_with_published_knowledge_flags` → **1 passed**.
**Quirk preserved:** `_ensure_schema` has byte-identical if/else branches (114–147) — only `ts_default` (`CURRENT_TIMESTAMP::text` vs `datetime('now')`), computed before the branch, differs between prod/sqlite dialects. Porters should collapse the duplication.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase-memory.search_graph({ project: "mnt-hdd-utopia-inspo-cuga-agent", query: "config_store load_config draft version agent_configs", limit: 10 });
```
(Executed pre-write; `get_code_snippet` retrieved `save_config` 168–195 live from the graph.)

## Verdict
Adopt the single-table draft/published duality with explicit draft exclusions in every read path, MAX+1 string-version append, and the dual-context `run_sync` bridge. Adapt tenant/instance keying and the '--draft' suffix convention to your host. Omit nothing from the merge-fill key list if you keep partial-edit semantics — dropping `env` or `cwd` silently breaks launches.

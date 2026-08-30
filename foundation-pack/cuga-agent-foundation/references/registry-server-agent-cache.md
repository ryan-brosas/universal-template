<!-- capsule-v2 -->
# Per-agent registry cache in a tool server — how does one FastAPI process serve isolated MCP tool sets for many agents, including config reload and teardown?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** You're exposing tools over HTTP to multiple agents whose tool catalogs differ per agent — what's the lifecycle (create/cache/reload/shutdown) of per-agent registries, and how do YAML vs database modes differ?

## Global dict[(MCPManager, ApiRegistry)] keyed by AGENT_ID; 'none' config path flips the whole server into DB mode
**Path/Symbol:** `src/cuga/backend/tools_env/registry/registry/api_registry_server.py` — `agent_registries: Dict[str, tuple[MCPManager, ApiRegistry]]` :25 + `database_mode` :26 + `default_agent_id` :27, `_get_agent_id` :85-87 (`AGENT_ID` env, default `cuga-default`), `get_config_filename` :61-74 (`MCP_SERVERS_FILE=none` ⇒ database mode; missing file raises FileNotFoundError), `_get_or_create_registry` :90-157, `lifespan` :160-189, `/reload` :468-540, `/clear_cache` :543-573, knowledge transport override :126-150.
**Signature:** `async _get_or_create_registry(agent_id, retry_on_empty=False) -> tuple[MCPManager, ApiRegistry]`; every endpoint takes `agent_id: Optional[str] = Query(None)` and routes `if database_mode and agent_id` → cached-per-agent else → global default.
**Data Shape:** YAML mode = one shared config, all agents identical; DB mode = `load_service_configs_from_db(agent_id)` per agent, empty-config retry once after 1s (`retry_on_empty`) to survive create-then-immediately-call races.

### Decisive source
```python
# :481-493 /reload in DB mode — pop+shutdown BEFORE recreate; default-agent
# reload must re-point the GLOBALS or old tools keep serving
if agent_id in agent_registries:
    old_mgr, _ = agent_registries.pop(agent_id)
    await old_mgr.shutdown()
await _get_or_create_registry(agent_id, retry_on_empty=True)
if agent_id == default_agent_id:
    mcp_manager, registry = agent_registries[agent_id]
```
**Flow:** lifespan reads config filename → "none" sets `database_mode`, pre-creates default agent | else loads YAML once. Request with agent_id → cache hit returns pair; miss builds services (DB w/ retry or shared YAML) → overrides knowledge service transport to HTTP when KnowledgeConfig says so (url/readiness_url/ready_values rewritten, stdio fields nulled) → `MCPManager(config)` + `ApiRegistry` + `start_servers()` → cache. Shutdown closes every cached manager.
**Invariant:** (1) Registry creation is lazy PER AGENT and cached forever until explicit `/reload` or `/clear_cache` (400 in YAML mode). (2) Reload order matters: shutdown-old BEFORE recreate-with-retry; re-point globals only when reloading the default agent. (3) The knowledge-service override is best-effort inside try/except — an unconfigured KB must not break registry boot for non-KB agents. (4) `/api/reset` clears auth tokens AND nulls auth_manager.

**Probe:** No direct unit suite at HEAD for the server module itself (coverage caveat — composition layer over MCPManager; behavior exercised via sdk_core integration tests `tests/test_policy_reset_and_reload.py` and e2e_helpers). Source-read verified at pinned commit.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "_get_or_create_registry agent_id database mode reload clear_cache", limit: 8 });
```
## Verdict
Adopt per-tenant (agent) service caches keyed by explicit request param for multi-agent tool servers; keep the global-default fallback so legacy single-agent clients need no changes. Adapt retry timing. Omit the transport override if you have no dual-transport service like knowledge.

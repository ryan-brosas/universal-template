<!-- capsule-v2 -->
# Server lifespan twin-graph startup — how does one process boot prod AND draft agent universes without letting a failed subsystem kill startup?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-cuga-agent`. **Question:** How do I port a FastAPI lifespan that boots multiple optional subsystems (policy, knowledge, browser env, side-car servers) so any single failure degrades to a status instead of aborting, and so published user config survives restarts?

## Lifespan: concurrent fail-open init + dual DynamicAgentGraph twins
**Path/Symbol:** `src/cuga/backend/server/main.py:lifespan` (543–1184), with `initialize_knowledge_engine` (680–807) stored on app_state for on-demand reuse by manage routes.
**Signature:** `@asynccontextmanager async def lifespan(app: FastAPI)`.
**Data Shape:** mutates module singletons `app_state` / `draft_app_state`: `policy_system`, `policy_filesystem_sync`, `knowledge_engine`, `knowledge_provider`, `internal_token`, `agent`, `tools_include_by_app`, `config_version`, `background_tasks`, `save_reuse_process`; subsystem states reported via `set_subsystem_status(name, starting|ready|failed|disabled, msg, details?)`.

### Decisive source
```python
app_state.initialize_knowledge_engine = initialize_knowledge_engine  # manage routes call it on demand
...
await asyncio.gather(_init_policy(), _init_knowledge())   # subsystems boot concurrently, each try/except-degraded
...
app_state.agent = DynamicAgentGraph(None, langfuse_handler=..., policy_system=app_state.policy_system,
    tool_provider=tool_provider, llm_config=_startup_llm_cfg or None,
    enable_todos=_prod_overrides.get("enable_todos"), ...)   # PROD twin, agent_id "cuga-default"
await app_state.agent.build_graph()
draft_agent_id = f"cuga-default--{draft_version}"          # DRAFT twin mirrors prod ctor
...
yield
for task in app_state.background_tasks: task.cancel()
await asyncio.gather(*app_state.background_tasks, return_exceptions=True)
if ... app_state.knowledge_engine: await app_state.knowledge_engine.aclose(); app_state.knowledge_engine.shutdown()
try:
    from cuga.backend.storage.facade import get_storage
    await get_storage().close_relational_stores()   # regression guard: dropping this leaked pg pool / left WAL residue
except Exception as e: logger.debug(f"close_relational_stores: {e}")
```

**Flow:** seed_secrets_from_env (fail-debug) → optional CUGA_LOAD_POLICIES hardcoded instructions → gather(policy init, knowledge init): policy = PolicyConfigurable.get_instance().initialize() then folder-sync ladder (sync disabled → None; auto-load off → sync-without-load; folder exists → load_policies_from_folder(clear_existing=False) + re-initialize + validate_and_sync; any error → warn + policy_system=None), knowledge = idempotent engine build + session-override/citations lookups wired into knowledge.sources + background warmup task (+ MCP HTTP daemon thread when transport=http) → manager-mode config apply + registry POST /reload → save_reuse subprocess (uv run, 6s settle) → deferred imports (browser stack deliberately NOT imported at module top — startup-latency optimization) → ExtensionEnv or BrowserEnvGymAsync + tracker experiment + env.reset() → **replay published config**: LLM via _apply_published_config and knowledge via apply_knowledge_config (disk secrets are stripped; engine falls back to env keys) → seed knowledge_config_hash for first-request collection routing → prod graph build → draft mirror incl. own `<base>_draft` PolicyStorage + CombinedToolProvider + graph build → GC ephemeral stream events → warm shortlister catalogue → yield → shutdown ladder above.
**Invariant:** a subsystem failing must never abort startup — it lands in subsystem status `failed` with the error in details, partial engines are torn down (aclose awaited, shutdown called, app_state.knowledge_engine=None), and the server still serves. Draft falls back to prod policy_system when it has none.
**Probe:** `tests/unit/test_knowledge_init_failure_isolation.py` (executed this run: 6 passed) — asserts exception swallowed, status["state"]=="failed", engine None, aclose awaited once.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-cuga-agent", query: "lifespan initialize_knowledge_engine set_subsystem_status", limit: 10 });
```

## Verdict
Adopt the concurrent fail-open init ladder, the subsystem-status machine, published-config replay over settings.toml, and the shutdown ordering ending in close_relational_stores. Adapt draft-twin naming (`--draft` suffix, separate vector collection) to your store's identifier rules. Omit the macOS/Windows auto-open-browser UX and demo OOBE seeding.

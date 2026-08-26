<!-- capsule-v2 -->
# Orchestrator bootstrap & token ledger — how do lanes, cumulative token accounting, and browser mode get established BEFORE run(), and what fires at import time?

**Source:** TheAgenticBrowser (TheAgentic Community License 1.0 — source-available; SaaS-competing-use restricted) `main@71daa28`; Codebase Memory `mnt-hdd-utopia-inspo-TheAgenticBrowser`. **Question:** What must an orchestrator initialize so three agent lanes stay independently accounted and API-mode gets a headless evidence-collecting browser without touching run()'s loop body?

## __init__ state block → token ledger → two-phase async_init
**Path/Symbol:** `core/orchestrator.py`: class-level `logfire.configure(send_to_logfire='if-token-present', scrubbing=False)` (:171), `__init__` (:173-195), `update_token_usage` (:198-201), `log_token_usage` (:203-214), `async_init(session_id, start_url)` (:216-231), `initialize_browser_manager` (:261-270). Call sites of the ledger inside run(): planner :376, browser :443-447, critique :553-557. Entry context: `core/main.py` (10L) is just `Orchestrator()` + `await start()`.
**Signature:** `def update_token_usage(self, agent_type: str, usage: Usage)`; `def log_token_usage(self, agent_type: str, usage: Usage, step: Optional[int] = None)`; `async def async_init(self, session_id: Optional[str] = None, start_url: Optional[str] = None)`.
**Data Shape:** Per-lane ledgers: `cumulative_tokens = {planner|browser|critique: {'total': 0, 'request': 0, 'response': 0}}`; parallel `message_histories = {'planner'|'browser'|'critique': []}`; flags `terminate`, `session_id`, `current_url`, `iteration_counter`, `shutdown_event`, and `ss_enabled = os.getenv('AGENTIC_BROWSER_SS_ENABLED', 'false').lower() == 'true'` (screenshot verification is env-OPT-IN).

### Decisive source
```python
# :171 — IMPORT-TIME global telemetry side effect, scrubbing OFF
class Orchestrator:
    logfire.configure(send_to_logfire='if-token-present', scrubbing=False)
# :443-447 — ledger fed from pydantic-ai result PRIVATE usage
self.log_token_usage(
    agent_type='browser',
    usage=browser_response._usage,
    step=self.iteration_counter
)
# :219/:227-231 — default start page is google.com; init navigation fails LOUD
self.current_url = start_url or "google.com"
try:
    await self.browser_manager.navigate_to_url(self.current_url)
except Exception as e:
    logger.error(f"Failed to navigate to initial URL: {str(e)}")
    raise
```

**Flow:** sync `__init__` builds client + empty lane ledgers (NO browser yet) → caller invokes `async_init` (two-phase construction): creates PlaywrightManager via `initialize_browser_manager` — `input_mode == "API"` ⇒ `PlaywrightManager(gui_input_mode=False, take_screenshots=True, headless=True)`, else GUI singleton defaults — then `async_initialize()` then navigates to `start_url or "google.com"`, re-raising on failure → run() calls `log_token_usage` after EACH agent turn, which accumulates into the lane dict AND emits iteration-vs-cumulative logfire lines.
**Invariant:** Lane separation is structural: histories AND token totals are per-agent dicts keyed identically (`planner/browser/critique`) — never merge them; cost attribution and critique-input filtering both depend on it. Browser creation lives ONLY in async_init's guarded branch (idempotent via `if not self.browser_manager`). Importing this module reconfigures GLOBAL logfire with scrubbing disabled — DOM content can reach your telemetry backend; porters must either re-enable scrubbing or strip the class attribute.
**Probe:** `cd /mnt/hdd/utopia/inspo/TheAgenticBrowser && grep -c "scrubbing=False" core/orchestrator.py` → `1` (:171); `grep -n "\._usage" core/orchestrator.py` → `:378 (planner), :445 (browser), :555 (critique)`; `grep -c "cumulative_tokens\[" core/orchestrator.py` → `6` (:199-201 accumulate, :210-212 log); `grep -n "google.com" core/orchestrator.py` → `:219`. Coverage caveat: repo ships no tests.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-TheAgenticBrowser", query: "log_token_usage cumulative_tokens async_init initialize_browser_manager", limit: 10 });
```

## Verdict
Adopt: per-lane cumulative token ledger fed from each agent result, two-phase init that owns browser bring-up + start-page navigation with loud failure, and env-opt-in screenshot verification. Adapt: the default start URL, the headless/screenshots fork for API mode, and your telemetry config. Fix-at-port: read public usage accessors instead of `_usage`; re-enable logfire scrubbing or remove the import-time side effect. Omit: IST/logfire presentation details. Caveat: no upstream tests; graph coverage `no_recorded_issue` at generation `2026-08-23T00:02:33Z`.

<!-- capsule-v2 -->
# Per-action hang-guard timeout — how does every action return within a bounded window even when its event handler hangs?

**Source:** browser-use MIT `main@3c989dc`; Codebase Memory `browser-use`. **Question:** how do you guarantee an agent action can never hang forever on a dead CDP WebSocket when the underlying event bus has no timeouts?

## Connected graph-selected seam
**Path/Symbol:** `browser_use/tools/service.py` — `_ACTION_TIMEOUT_FALLBACK_S` (:87), `_parse_env_action_timeout` (:91), `_DEFAULT_ACTION_TIMEOUT_S` (:146), `_coerce_valid_action_timeout` (:149), `Tools.act` (:2266 wrap site :2297).
**Signature:** `_parse_env_action_timeout(raw: str | None) -> float`; `_coerce_valid_action_timeout(value: float | None) -> float`; `async def act(self, action: ActionModel, browser_session, ..., action_timeout: float | None = None) -> ActionResult`.

### Decisive source
```python
# Global per-action timeout: last-resort guard against hung event handlers.
# Individual CDP calls have their own shorter timeouts, but event-bus
# `await event` / `event_result()` calls have none — if a watchdog handler
# blocks on a dead CDP WebSocket, the action can hang past any agent-level
# watchdog. Default 180s sits above the longest built-in inner timeout — the
# extract action's page_extraction_llm.ainvoke at 120s — plus grace.
_ACTION_TIMEOUT_FALLBACK_S = 180.0

def _parse_env_action_timeout(raw):
    # Accepts ONLY finite positive values. Empty/non-numeric/nan/inf/negative/zero
    # fall back to default with a warning — otherwise every action would time out
    # immediately (nan) or never (inf/<=0).
    ...
result = await asyncio.wait_for(
    self.registry.execute_action(action_name=action_name, params=params, ...),
    timeout=timeout_s,
)
except TimeoutError:
    result = ActionResult(error=f'Action {action_name} timed out after {timeout_s:.0f}s. ...')
```

**Flow:** env var `BROWSER_USE_ACTION_TIMEOUT_S` parsed defensively at import → caller override via `tools.act(action_timeout=...)` coerced by the same finite-positive guard (None ⇒ env-derived default) → `act()` wraps `registry.execute_action` in `asyncio.wait_for(timeout_s)` → `TimeoutError` (both the cap AND any inner handler TimeoutError) becomes an `ActionResult(error=...)` telling the agent the browser may be unresponsive, never a raised exception.
**Invariant:** nan/inf/non-positive values must DEGRADE TO DEFAULT, never disable or invert the guard (a porter who passes raw user input through will make every action either instant-timeout or hang forever); the default must stay above the extract action's inner 120s LLM cap or slow-but-valid extractions get truncated.
**Probe:** `tests/ci/test_action_timeout.py` — `test_act_enforces_per_action_timeout_on_hung_handler` (:36 elapsed < sleep/2, error contains 'timed out' + action name), `test_act_rejects_invalid_action_timeout_override` (:94 nan/inf/0/-5 all fall back), `test_default_action_timeout_accommodates_extract_action` (:123 ≥150s), `test_malformed_env_timeout_does_not_break_import` (:153 module reload yields 180.0).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-use", query: "_parse_env_action_timeout _coerce_valid_action_timeout Tools.act asyncio.wait_for", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-layer ladder (env parse guard → caller coerce guard → wait_for cap converting to error-result); adapt the 180s number to your own longest inner timeout; omit the Laminar span plumbing around it.

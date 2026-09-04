<!-- capsule-v2 -->
# Agent telemetry event envelope — how do you fold a whole agent run into one privacy-shaped analytics event?

**Source:** browser-use MIT `main@85ddbfedf609`; Codebase Memory `browser-use`. **Question:** what does a run-level product-analytics event carry, how is it constructed from history without leaking host details, and what do positional None slots mean?

## Connected graph-selected seam
**Path/Symbol:** `browser_use/telemetry/views.py` whole (88L) — `BaseTelemetryEvent` (:9-21), `AgentTelemetryEvent` (:24-58), MCP client/server twins (:61-88); construction at `browser_use/agent/service.py` `Agent._log_agent_event` (:2183-2246) and beta twin (`beta/service.py:4743-4797`, adds `agent_type='rust_core'`).
**Signature:** `BaseTelemetryEvent.properties -> dict` (derived); `Agent._log_agent_event(max_steps: int, agent_run_error: str | None = None) -> None`.
**Data Shape:** ABC dataclass with abstract `name` property shadowed by subclass FIELD defaults; four event sections: start details / step details / end details / judge details.

### Decisive source
```python
@dataclass
class BaseTelemetryEvent(ABC):
	@property
	@abstractmethod
	def name(self) -> str: ...
	@property
	def properties(self) -> dict[str, Any]:
		props = {k: v for k, v in asdict(self).items() if k != 'name'}
		props['is_docker'] = is_running_in_docker()   # ALWAYS injected deployment context
		return props

# AgentTelemetryEvent subclasses set name as a FIELD: name: str = 'agent_event'

def _log_agent_event(self, max_steps, agent_run_error=None):
	action_history_data = []
	for item in self.history.history:
		if item.model_output and item.model_output.action:
			step_actions = [a.model_dump(exclude_unset=True) for a in item.model_output.action if a]
			action_history_data.append(step_actions)
		else:
			action_history_data.append(None)          # POSITIONAL slot: step had no actions
	...
	cdp_url=urlparse(self.browser_session.cdp_url).hostname   # HOST ONLY, never full URL
	if self.browser_session and self.browser_session.cdp_url else None,
	success=self.history.is_successful(),
	judge_verdict=judgement_data.get('verdict') if judgement_data else None,
```
**Flow:** run end → `_log_agent_event` folds history into per-step action dumps (positionally aligned with steps, `None` where a step produced no actions), extracts final result JSON only when present, pulls judge verdict fields via `history.judgement()` and token totals from `token_cost_service.get_usage_tokens_for_model` → single `AgentTelemetryEvent` capture → `properties` derives the posthog payload minus `name` plus `is_docker`.
**Invariant:** `cdp_url` must be reduced to `urlparse(...).hostname` — the wire never carries paths/query strings of the CDP endpoint (beta direct tests pin this: `wss://cloud-browser.example/.../session` records as `cloud-browser.example`); `action_history[i] is None` means "step i ran without actions", distinct from `[]`; the `name`-as-field shadowing means `asdict()` would include it — hence properties MUST filter it out before adding `is_docker`. Beta twin additionally filters reconstructed URLs (drops empty/127.0.0.1 entries).

**Probe:** executed live (repo .venv): constructed minimal `AgentTelemetryEvent` — `name == 'agent_event'`, `is_docker in properties`, `'name' not in properties`, all five `judge_*` fields default None. Direct tests executed GREEN: `test_beta_agent_telemetry_filters_empty_reconstructed_urls` (urls_visited == ['https://example.com'], agent_type 'rust_core') and `test_beta_agent_telemetry_records_cloud_cdp_hostname` (cdp_url hostname-only) — 7 passed with test_config.py.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-use", query: "AgentTelemetryEvent BaseTelemetryEvent _log_agent_event is_docker cdp_url hostname judge_verdict", limit: 8, fields: ["lines"] });
```

## Verdict
Adopt the one-event-per-run envelope with sectioned fields, the derived-properties pattern that strips identity keys and injects environment context, and hostname-only endpoint recording as the privacy floor. Adapt field sections to your product's funnel. Omit the judge_* section if you have no eval loop. Keep the None-vs-empty-list distinction — downstream analysts rely on it.

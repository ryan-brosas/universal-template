<!-- capsule-v2 -->
# PlaywrightBrowser capability shell: lazy launch, per-run isolation, durable-execution refusal

## Source / Question
`pydantic_ai_harness/playwright/_capability.py` (365L whole file) @ `main@f971198` (PR #420) — A stateful Chromium behind an agent capability: when does the browser start, how do concurrent runs stay isolated, and why must durability be REFUSED at construction rather than discovered mid-run?

## Path / Symbol
`playwright/_capability.py` — `PlaywrightBrowser(AbstractCapability)` (:76–136), egress shorthand/policy exclusivity in `__post_init__` (:250–258), `for_agent` durability guard (:276–300), `for_run` per-run copy (:302–304), `wrap_run` session scoping (:320–330), `from_spec` credential exclusion (:332–353), `_INSTRUCTIONS` template (:34–73).

## Signature
```python
@dataclass
class PlaywrightBrowser(AbstractCapability[AgentDepsT]):
    headless: bool = True
    allowed_domains: list[str] | None = None      # egress allowlist shorthand…
    block_private_addresses: bool = True          # …independent SSRF-class block, default ON
    policy: EgressPolicy | None = None            # full policy; MUTUALLY EXCLUSIVE with both shorthands
    chromium_sandbox: bool = True                 # ON by default — unlike Playwright itself
    auto_install_chromium: bool = False           # a library should not download a browser as a side effect
    storage_state / cdp_url                       # repr=False, absent from from_spec
def for_agent(self, agent) -> AbstractCapability[AgentDepsT]   # raises UserError on BaseDurabilityCapability sibling
async def for_run(self, ctx) -> PlaywrightBrowser[AgentDepsT]: return replace(self)
```

## Data Shape
One `PlaywrightBrowserSession` + toolset built in `__post_init__`; policy object is THE single decision-maker ("set those fields on the policy instead, so one object decides", :252–254). Instructions template interpolates `{max_content_tokens}` and `{allowed_domains}` from `policy.describe()` so the model's stated reach can't drift from enforced reach.

### Decisive source
Durability guard rationale (:278–289): "durability replays tool calls as activities and a live Chromium page cannot survive replay or worker restart… Detection matches `BaseDurabilityCapability`, the shared base of the bundled Temporal/DBOS/Prefect integrations. Pydantic AI exposes no public marker for the durability tier, and the `innermost` ordering position is not one: `InputGuard` also declares `innermost`, so ordering alone would reject the supported guard-plus-browser composition." Per-run isolation (:302–303): "Return a fresh instance per run so concurrent runs never share a page or browser." Lazy launch (:322–324): "Chromium starts on the first browser-tool call, not here, so a run that never browses never launches one. The run's tracer is adopted here." Sandbox default (:196–203): this capability opens pages nobody vetted; disabling it accepts that a renderer exploit runs with the agent's own access. `storage_state` is an OBJECT not a path "so the capability never assumes a filesystem it can read" (:227–230); `from_spec` deliberately cannot carry it or `policy` ("a spec naming it raises rather than moving cookies into whatever stores the spec").

**Flow:** construction validates policy XOR shorthands → `for_agent` walks `agent.root_capability.apply(siblings.append)` refusing durability siblings → each run gets `replace(self)` → `wrap_run` sets tracer + `async with self._session` → first browser tool triggers launch under lock → teardown however the run ends.
**Invariant:** missing-binary failures surface as a `playwright install chromium` TOOL RESULT (`BrowserUnavailableError`→result + process `BrowserUnavailableWarning`) so a shell-capable agent can recover, not a dead run.

## Probe (direct test)
`tests/playwright/test_playwright.py` — 310 tests incl. capability-construction matrix (policy+shorthand UserError), durability-refusal case, per-run isolation via `for_run`. Smoke script `scripts/playwright_smoke.py` covers live-Chromium scenarios (dialog/tab/private-name/iframe).

## Retrieve
```
search_graph --project pydantic-ai-harness --name-pattern 'PlaywrightBrowser for_run wrap_run' --detail ids
# File node: pydantic_ai_harness.pydantic_ai_harness.playwright._capability.__file__
```

## Verdict
**Adopt** lazy-launch + per-run instance + construction-time durability refusal pattern for ANY non-checkpointable resource capability. **Adopt** the honest-hint failure mode for missing binaries. **Adapt** instruction text. **Omit** CDP-provider specifics if you have no managed-browser story.

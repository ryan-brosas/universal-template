<!-- capsule-v2 -->
# Agent step loop — phased step with centralized error handling and stale-state clearing

**Source:** browser-use MIT `<branch>@<commit>`; Codebase Memory `browser-use`. **Question:** how does an agent loop stay debuggable and crash-safe when every phase (browser state, LLM, tool exec) can fail differently?

## Connected graph-selected seam
**Path/Symbol:** `browser_use/agent/service.py` (4,166 lines): `Agent` (:133), `step` (:1029-1079) — the canonical loop; `_prepare_context` (:1081+), `_get_next_action`, `_execute_actions`, `_post_process`, `_handle_step_error` (:1076), `_finalize`; `_setup_action_models` (:774) with forced-`done` model at max_steps; `log_response` (:89); skills-as-actions registration (`_register_skills_as_actions` :830).
**Signature:** `step()` = Phase 0 captcha-wait → Phase 1 `_prepare_context` → clear stale state → Phase 2 `_get_next_action` + `_execute_actions` → Phase 3 `_post_process`; ALL exceptions funnel into one handler; `_finalize` runs in `finally`.
**Data Shape:** per-step: `BrowserStateSummary` (dom/screenshot/url/events) → `AgentOutput` (structured action list) → `list[ActionResult]` (with `long_term_memory` strings fed back to the LLM).

### Decisive source
```ts
async def step(self, step_info=None):
    self.step_start_time = time.time()      # timing FIRST — before any exception path
    browser_state_summary = None
    try:
        # Phase 0: captcha watchdog may block; outcome injected as ActionResult
        # so the LLM sees 'Waited Xs for vendor CAPTCHA. Result: success.'
        captcha_wait = await self.browser_session.wait_if_captcha_solving()
        ...
        browser_state_summary = await self._prepare_context(step_info)
        # CRITICAL: clear AFTER context prep (which renders previous result),
        # BEFORE llm call — a timeout can't leave stale data from last step
        self.state.last_model_output = None
        self.state.last_result = None
        await self._get_next_action(browser_state_summary)
        await self._execute_actions()
        await self._post_process()
    except Exception as e:
        await self._handle_step_error(e)     # ONE place classifies + recovers
    finally:
        await self._finalize(browser_state_summary)
```

**Flow:** each step snapshots full browser state (screenshot always captured for replay even without vision) → page-specific actions merged into the action model → messages built → LLM returns structured actions → executed sequentially with results as memory → post-process (downloads check, gif frame). Errors are classified centrally: rate-limit vs timeout vs browser-crash get different recovery (pause, retry, reattach).
**Invariant:** step timing starts before anything can throw; stale step state cleared at exactly one point (after context render, before LLM); every failure flows through one handler; forced-`done` action model prevents infinite loops at max_steps; external waits (captcha) are surfaced to the LLM as memory, never silently swallowed.
**Probe:** `tests/agent/` tests (step completes on mock llm; error classification; done-forced at max_steps; captcha outcome in results).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-use", query: "Agent step _prepare_context _handle_step_error _finalize max_steps done", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the phased step loop (prepare → clear-stale → act → post → single error handler → always-finalize) and forced-done termination; adapt phases to host's modality.

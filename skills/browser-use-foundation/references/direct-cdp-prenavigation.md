<!-- capsule-v2 -->
# Direct CDP pre-navigation — how do you execute initial navigation yourself and still tell the core not to repeat it?

**Source:** browser-use MIT `main@3c989dc`; Codebase Memory `browser-use`. **Question:** when initial_actions is a pure navigation list and the session already speaks CDP, how do you navigate directly, verify it landed, and rewrite the task so the agent continues instead of re-navigating?

## Connected graph-selected seam
**Path/Symbol:** `browser_use/beta/service.py` — `Agent._execute_direct_initial_navigation_actions` :6069, state probe `_capture_direct_initial_navigation_state` (:6120, 7s deadline, 0.25s poll), URL matcher `_direct_initial_navigation_state_matches` (:6145), context builder `:6169`, task rewrites `_task_with_completed_initial_navigation_context` (:1307) + `_task_with_initial_actions` (:1277), start-URL extraction `_extract_start_url` (:1397); gate `_direct_initial_navigation_enabled` :1200 (env `BROWSER_USE_RUST_DIRECT_INITIAL_NAVIGATION`, default ON).
**Signature:** `async _execute_direct_initial_navigation_actions() -> list[ActionResult] | None` — None ⇒ "not handled", caller falls back to terminal-run execution.
**Data Shape:** nav actions recognized by name ∈ {`open_tab`, `go_to_url`, `navigate`} with string `url`; completed-state context `{requested_url, url?, title?, tabs?}` recorded per hop in `_completed_initial_navigation_urls/states`.

### Decisive source
```python
if not (_extract_cdp_url(self.browser_session) or _extract_profile_cdp_url(self.browser_profile)):
    return None                      # direct path ONLY for existing CDP sessions
for url, new_tab in nav_actions:
    await navigate_to(url, new_tab=new_tab)
    state = await self._capture_direct_initial_navigation_state(url)   # poll until URL matches or 7s
    if not self._direct_initial_navigation_state_matches(url, getattr(state,'url','')):
        self._completed_initial_navigation_urls = []   # ABORT: hand navigation back
        self._completed_initial_navigation_states = []
        return None   # 'Leaving navigation in the Rust task context.'
# matcher: same netloc AND path equal (both '/'-rstrip'ed; requested '/' matches any)
# AND query equal only if requested had one  → redirects within the page are OK
# task rewrite after completion (single URL case):
'The browser session is already open at {url!r}. Continue from the current page. '
'Your first browser step should inspect or extract from the current page before any repeat navigation. '
'Do not navigate to that same start URL again unless browser status shows a different URL.' + observed-state lines
```

**Flow:** enabled-gate → requires CDP session + callable `navigate_to` + ALL actions being navigations → navigate each → verified-poll (returns last seen state at deadline; mismatch aborts the WHOLE batch and returns None) → on success append ActionResult with "Navigated to …" memory → `_run_terminal` stashes these history items as `_pending_history_prefix` and rewrites the task with "already open at" framing + observed `requested=/current_url=/title=` lines before the SDK call ever starts.
**Invariant:** verification-before-claim is mandatory — an unconfirmed navigation must NOT be reported as done nor marked complete (all-or-nothing batch reset); the rewritten task must both forbid repeat navigation and instruct inspection-first, otherwise the model burns its first turn re-navigating; prefix history preserves step numbering for consumers.
**Probe:** `tests/ci/test_beta_agent.py:6298` `test_beta_agent_run_pre_navigates_cdp_session_before_sdk_by_default` (asserts `navigate_to` called, task contains 'The browser session is already open at', and NOT 'First navigate to'), `:6353` `test_beta_agent_run_keeps_initial_navigation_when_direct_state_mismatches`, `:6627`/`:6666` default-on/env-off.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-use", query: "_execute_direct_initial_navigation_actions _capture_direct_initial_navigation_state", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the execute→verify→rewrite-task triad plus the None-means-fallback contract for pre-running deterministic prefixes against a live session; adapt action names and the matcher's redirect tolerance; omit the env kill-switch if you have no legacy path to preserve.

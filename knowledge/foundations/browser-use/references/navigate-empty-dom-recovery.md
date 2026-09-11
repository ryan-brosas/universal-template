<!-- capsule-v2 -->
# Navigation empty-DOM retry + error taxonomy — how does navigate distinguish "slow SPA" from "site unavailable" from "dead CDP"?

**Source:** browser-use MIT `main@3c989dc`; Codebase Memory `browser-use`. **Question:** what does the navigate action do between dispatching NavigateToUrlEvent and returning ActionResult, and how are failures classified?

## Connected graph-selected seam
**Path/Symbol:** `browser_use/tools/service.py` — `navigate` action (:489-577), `_page_appears_empty` helper (:507), error classifier (:556-577); `search` engine table (:443); `wait` cap (:591).
**Signature:** `_page_appears_empty(s) -> bool` (closure); error ladder on `except Exception`.

### Decisive source
```python
# Health check: detect empty DOM for http/https pages and retry once.
# Uses _root is None (truly blank) OR empty llm_representation() (SPA not yet rendered).
# NOTE: llm_representation() returns a NON-EMPTY placeholder when _root is None,
# so we must check _root is None separately — the repr string alone would lie.
def _page_appears_empty(s) -> bool:
    return s.dom_state._root is None or not s.dom_state.llm_representation().strip()

if url_is_http and _page_appears_empty(state):
    await asyncio.sleep(3.0); recheck
    if still empty: reload + sleep(5.0) + final check ->
        return ActionResult(error='...may require JavaScript that failed to render,
                                    use anti-bot measures, or have a connection issue')

# Error classification ladder:
if isinstance(e, RuntimeError) and 'CDP client not initialized' in error_msg:
    return ActionResult(error=f'Browser connection error: ...')       # infra failure
elif any(err in error_msg for err in ['ERR_NAME_NOT_RESOLVED','ERR_INTERNET_DISCONNECTED',
        'ERR_CONNECTION_REFUSED','ERR_TIMED_OUT','ERR_TUNNEL_CONNECTION_FAILED','net::']):
    return ActionResult(error=f'Navigation failed - site unavailable: {url}')  # site failure
else:
    return ActionResult(error=f'Navigation failed: {str(e)}')         # generic
```

**Flow:** dispatch NavigateToUrlEvent → await event + result → (same-tab only) empty-DOM health gate with 3s/5s escalation ladder ending in an actionable error message → success memory differs for new-tab vs same-tab. The companion `wait` action clamps to ≤30s and subtracts 1s (documented as reverted-then-rekept heuristic).
**Invariant:** the `_root is None` separate check is load-bearing (placeholder repr masks blank pages); health gating applies ONLY to http/https (file:// and chrome:// legitimately have no DOM); Chrome net-error strings classify SITE problems so the LLM retries a different URL rather than blaming the browser.
**Probe:** `tests/ci/test_action_blank_page.py`, `tests/ci/test_multi_act_guards.py::test_navigate_terminates/:test_navigate_aborts_remaining_actions` (:109/:165).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase-memory.search_graph({ project: "browser-use", query: "navigate _page_appears_empty ERR_NAME_NOT_RESOLVED NavigateToUrlEvent empty DOM retry", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-probe emptiness test + bounded retry ladder + three-class navigation error funnel; adapt timeouts; omit the search-engine URL table if you have no search action.

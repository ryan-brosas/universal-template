<!-- capsule-v2 -->
# ActionResult envelope contract — tri-state success and dual memory channels

**Source:** browser-use MIT `main@85ddbfedf609`; Codebase Memory `browser-use`. **Question:** what should one action result carry so memory, errors, images, and observability all flow without the LLM prompt grammar special-casing each?

## Connected graph-selected seam
**Path/Symbol:** `browser_use/agent/views.py`: `ActionResult` (:307-349), validator `validate_success_requires_done` (:340-349); consumption fold `browser_use/agent/message_manager/service.py _update_agent_history_description` (:304-389).
**Signature:** `ActionResult(is_done: bool | None = False, success: bool | None = None, error, attachments, images, long_term_memory, extracted_content, include_extracted_content_only_once=False, metadata)`; `@model_validator(mode='after')`.
**Data Shape:** tri-state success — default `None`; annotation is `bool | None` even where default False (:311). Two documented memory channels: `long_term_memory` (persists every step) vs `extracted_content` + `include_extracted_content_only_once` (one-shot read-state update). `images` kept separate from text (`[{"name", "data": base64}]`); `metadata` dict for observability coordinates.

### Decisive source
```python
# :343-348 — success=True REQUIRES done; regular actions leave success None
if self.success is True and self.is_done is not True:
    raise ValueError(
        'success=True can only be set when is_done=True. '
        'For regular actions that succeed, leave success as None. '
        'Use success=False only for actions that fail.')

# :315-337 (fold) — wipe-once-only channels at the TOP of every step...
self.state.read_state_description = ''
self.state.read_state_images = []
# ...once-only extracted_content -> <read_state_N> tags; images one-shot;
# long_term_memory persists; elif extracted_content WITHOUT once-only ALSO persists;
# error middle-elision [:100] + '......' + [-100:] past 200 chars; dual 60k caps.
```

**Flow:** actions/judges/consumers construct results -> validator enforces the success ladder at construction time -> per step the message manager wipes one-shot channels, folds once-only content into `<read_state_N>` tags, appends persistent memory under a `Result\n` header with explicit `[Content truncated at 60k characters]` markers -> producers found across the repo: Agent._execute_ai_step, mcp/client tool registration, beta twin.
**Invariant:** `success=True ∧ ¬is_done` is UNCONSTRUCTABLE (exact validator message probed); `ActionResult()` alone is valid (success None, is_done False); bare `success=False` is legal (failure of a non-done action). Consumer pinning: tests/ci/test_rerun_ai_summary.py :12-54 builds `ActionResult(long_term_memory='Step 1 completed')` with success LEFT NONE. Message-path secret hygiene pinned by EXECUTED test tests/ci/security/test_sensitive_data.py::test_sensitive_data_filtered_from_action_results (real values replaced back to `<secret>password</secret>` before LLM messages) — executed this pass, 4 passed in 0.09s incl. chrome-profile helpers.
**Probe:** `.venv/bin/python -c` from repo root: default → success None/is_done False; `ActionResult(success=True)` → ValidationError with the exact message; `(is_done=True, success=True)` OK; `success=False` alone OK (executed this pass).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-use", query: "ActionResult success is_done long_term_memory extracted_content", limit: 10 });
```
Executed during discovery: rank-1 `validate_success_requires_done` :341-349.

## Verdict
Adopt the tri-state success ladder and the two-channel memory split verbatim — they are what let terminal predicates stay last-result-wins simple (see history-terminal-predicates) and keep one-shot reads out of permanent context. Adapt channel names to your host. Omit the deprecated `include_in_memory` flag. Coverage caveat: no dedicated views.py unit test exists; consumer test + validator probe stand in as evidence.

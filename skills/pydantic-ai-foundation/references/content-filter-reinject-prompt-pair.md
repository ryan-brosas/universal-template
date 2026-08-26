<!-- capsule-v2 -->
# Opt-in content-filter escalation + system-prompt reinjection — response-side error policy and history-repair defaults

## Source / Question
`pydantic_ai_slim/pydantic_ai/capabilities/content_filter.py` + `capabilities/reinject_system_prompt.py` @ `main@b3cdbc96` (MIT); Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** How should "provider content-filtered this response" escalate into a run-ending typed error WITH the partial body preserved, and how do you repair reconstructed histories that lost their system prompt without letting untrusted sources override the server's prompt? A porter will make filtering fatal by default or let frontend-supplied prompts win.

## Path / Symbol
`content_filter.py` — `RaiseContentFilterError(AbstractCapability)` (:16–47): finish_reason check (:34), body serialization via `ModelMessagesTypeAdapter.dump_json([response])` (:36), details ladder finish_reason→block_reason→refusal→generic (:38–45). `reinject_system_prompt.py` — `ReinjectSystemPrompt` (:17–77): `replace_existing` flag (:41–44), no-op-if-present gate (:52–55), agent system_prompt_parts resolution incl. ctx.model cast fallback (:57–74), `_has_system_prompt` (:80–84), `_strip_system_prompts` (drops empty requests entirely :87–97), `_prepend_to_first_request` (dataclass `replace` on first ModelRequest :100–102).

## Signature
```python
async def after_model_request(self, ctx, *, request_context, response: ModelResponse) -> ModelResponse
async def before_model_request(self, ctx, request_context: ModelRequestContext) -> ModelRequestContext
```

## Data Shape
ContentFilterError carries `body=` — the FULL serialized ModelResponse list — so callers inspect partial text/refusals after the raise. provider_details supplies the human message: `finish_reason` → `block_reason` → `refusal` → bare default.

### Decisive source
The conservative-by-default reinjection gate (:52–55):
```python
if self.replace_existing:
    _strip_system_prompts(messages)
elif _has_system_prompt(messages):
    return request_context   # ANY existing SystemPromptPart anywhere ⇒ untouched;
                             # existing prompts stay authoritative unless replace_existing=True
```

**Flow:** Content filter: OPT-IN capability — without it, filtered responses flow through normal classification; with it, any `finish_reason=='content_filter'` raises immediately post-request with diagnostics chosen from provider_details. Reinjection: runs before EVERY model request; presence scan over all ModelRequests; strip path removes SystemPromptParts (and DROPS requests left with zero parts rather than keeping empty shells); prepend path writes parts onto a replaced copy of the FIRST ModelRequest. UI adapters install it as `manage_system_prompt='server'` mode with `replace_existing=True` precisely because frontend histories are untrusted.

**Invariant:** Default posture preserves whatever system prompt already exists (handoffs/compaction survivors win); destructive replacement must be explicitly requested. The filter check happens AFTER the model call completes — the response object (with partial content) always exists to serialize.

**Probe:** `tests/test_agent.py` — `test_raise_content_filter_error...` family (:12171 asserts body[0]['parts'][0]['content'] == 'Partially generated content...', :12195 noop-for-stop, :12265 streaming variant, :12306). ReinjectSystemPrompt: imported/pinned in test_capabilities.py spec tables (:48/:176/:1739); ag-ui adapters document server-mode wiring (test_ag_ui.py:7027). Coverage caveat: no dedicated behavioral unit file for ReinjectSystemPrompt — pinned via spec-schema + adapter tests.

## Get live surrounding code
**Retrieve:**
```
search_graph --project mnt-hdd-utopia-inspo-pydantic-ai --query 'RaiseContentFilterError ReinjectSystemPrompt SystemPromptPart prepend'
```

## Verdict
**Adopt** opt-in escalation with body preservation and the diagnostic ladder; adopt presence-scan-default + explicit-strip reinjection for any host that rebuilds histories from untrusted stores. **Adapt** exception type naming to your host's taxonomy. **Omit** the refusal/block_reason branches if your providers expose only finish_reason.

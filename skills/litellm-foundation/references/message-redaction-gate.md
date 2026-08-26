<!-- capsule-v2 -->
# Message redaction gate — when logged payloads must lose prompts and completions

**Source:** litellm MIT `litellm_internal_staging@f005afa1460385a218be8ef1fdfa49998bf93523`; Codebase Memory `litellm`. **Question:** Under which precedence of dynamic params, request headers, and global settings does litellm strip messages/outputs from logging, and what exactly does it mutate versus copy?

## should_redact ladder + perform_redaction
**Path/Symbol:** `litellm/litellm_core_utils/redact_messages.py` — `should_redact_message_logging` (:295-344), `perform_redaction` (:229-292), entry `redact_message_input_output_from_logging` (:347-354), dynamic-param reader `_get_turn_off_message_logging_from_dynamic_params` (:357-374).
**Signature:** `redact_message_input_output_from_logging(model_call_details: dict, result, input: Any | None = None) -> Any`; `perform_redaction(model_call_details: dict, result, redact_streaming_responses: bool = True)`.
**Data Shape:** input is the shared `model_call_details` dict (mutated in place) plus the heterogeneous response object; output is either the original result or a deep-copied redacted one.

### Decisive source
```python
# redact_messages.py:317-344 (abridged) — precedence
if request_headers and bool(request_headers.get("litellm-disable-message-redaction", False)):
    return False                                   # explicit opt-out header wins over everything below
...
dynamic_turn_off: Final = _get_turn_off_message_logging_from_dynamic_params(model_call_details)
if dynamic_turn_off is not None:
    return dynamic_turn_off                        # per-request turn_off_message_logging (bool or str)
if is_redaction_enabled_via_header:                # litellm-enable-… or x-litellm-enable-…
    return True
return litellm.turn_off_message_logging is True    # global default

# redact_messages.py:238-242 — in-place mutation on the shared dict
model_call_details["messages"] = [{"role": "user", "content": "redacted-by-litellm"}]
model_call_details["prompt"] = ""
model_call_details["input"] = ""
```

**Flow:** gate first: disable-header → False; else dynamic param → its value; else enable-header(s) → True; else global flag. When redacting: `messages`/`prompt`/`input` are overwritten in place on the shared dict, `standard_logging_object` and vertex metadata are scrubbed via helpers, both `complete_streaming_response` and `async_complete_streaming_response` entries get content-stripped, and the *returned* result is a `copy.deepcopy` with choice contents / Responses-API output+reasoning / embedding `data` emptied. Coroutines, async generators, and unrecognized shapes cannot be deepcopied safely — they collapse to `{"text": "redacted-by-litellm"}`.
**Invariant:** The caller's dict is mutated in place (all later sinks see redacted values), but the returned response object is a copy — the real completion the caller receives is untouched. Redaction happens inside the Logging fan-out *before* hooks/sinks run. A disable-header alone can defeat an enabled dynamic param because it returns early.
**Probe:** `tests/test_litellm/litellm_core_utils/test_redact_messages.py` (`TestShouldRedactMessageLogging` :57-174, `TestPerformRedaction` :177-728) executed live at the pin → 35 passed.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "litellm", query: "should_redact_message_logging", limit: 2 });
// → rank-1 exact: redact_messages.should_redact_message_logging (redact_messages.py 295-344),
//   rank-2: TestShouldRedactMessageLogging (direct test class)
await mcp.codebase_memory.search_graph({ project: "litellm",
  query: "redact_message_input_output_from_logging", limit: 1 });
// → single hit: redact_messages.py 347-354
```

## Verdict
Adopt the four-rung precedence (dynamic param > disable-header > enable-header > global), in-place dict mutation + deep-copied response split, and the shape-collapse fallback for async/opaque results. Adapt the sentinel string and header names to your gateway's conventions; keep the deepcopy boundary or you leak unredacted completions to sinks that mutate payloads. Omit vertex-specific metadata scrubbing if you have no vertex plane. Coverage caveat: none — module fully read at :229-375 with direct tests green.

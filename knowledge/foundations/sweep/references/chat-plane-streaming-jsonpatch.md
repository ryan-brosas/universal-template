<!-- capsule-v2 -->
# Chat-plane streaming jsonpatch — how does the interactive chat surface stream LLM state to a browser, and how are code suggestions validated without ever being applied?

**Source:** sweep (Apache-2.0) `main@a8b8b67bda4f`; Codebase Memory `sweep`. **Question:** The ticket plane returns one final PR; the chat plane must instead stream a growing conversation to a browser UI while the model calls tools — what is the wire protocol, how are partial tool calls surfaced, and what happens to code the model proposes in chat?

## stream_state yields whole message lists; postprocessed_stream diffs them into RFC 6902 patches with in-band error ops
**Path/Symbol:** `sweepai/chat/api.py:chat_codebase` (:401–433, raises `ValueError("At least one message is required.")` :411), `chat_codebase_stream` (:451, raises `ValueError("No snippets were sent.")` :464, `EXPAND_SIZE = 100` :462, `use_openai = model.startswith("gpt")` :473), inner `stream_state` (:554, `for _ in range(5)` :571), `postprocessed_stream` (:767–784), code-suggestion annotation block (:714–760), `StreamingResponse` (:787). **Kernel reuse:** `validate_and_parse_function_call` (`sweepai/agents/modify_utils.py:625`), `get_error_message_dict` (`modify_utils.py:1428`; other caller `modify.py:154`), `extract_objects_from_string` (`sweepai/utils/str_utils.py:213`; other caller `review_utils.py:750`), `FileChangeRequest` construction (:745–751).

**Signature:** `stream_state(initial_user_message, snippets, messages, access_token, metadata, model, use_openai, k=DEFAULT_K) -> Generator[list[Message]]`; `postprocessed_stream(*args, **kwargs) -> Generator[str]` (each str is a jsonpatch document or an error-op document); `chat_codebase_stream(...) -> StreamingResponse`.
**Data Shape:** the client protocol is RFC 6902 ops over a JSON array of `Message.model_dump()` dicts; `Message.function_call` carries `{function_name, function_parameters, is_complete, snippets?}`; code suggestions ride `annotations["codeSuggestions"]` as `{filePath, originalCode, newCode, state: "pending", error}`.

### Decisive source
```python
for _ in range(5):                                   # :571 — hard cap on tool-call rounds
    stream = chat_gpt.chat_anthropic(
        content=user_message, model=model,
        stop_sequences=["</function_call>", "</function_calls>"],  # :575
        stream=True, use_openai=use_openai)
    ...
    for token in stream:
        if not token: continue
        result_string += token
        if len(result_string) < 50: continue         # :588 — withhold short prefixes
        current_string, *_ = result_string.split("<function_call>")
        if "<analysis>" in current_string:
            analysis = extract_xml_tag(current_string, "analysis", include_closing_tag=False) or ""
            user_response = extract_xml_tag(current_string, "user_response", ...) or ""
            self_critique = extract_xml_tag(current_string, "self_critique", ...)
            # XML tags map to roles: analysis→function, user_response→assistant, self_critique→function
            yield [*new_messages, *current_messages]  # whole-list snapshot, not deltas
    ...
    result_string = result_string.replace("<function_calls>", "<function_call>")  # :660
    result_string += "</function_call>"               # close the stop-truncated tag
    function_call = validate_and_parse_function_call(result_string, chat_gpt)     # modify_utils.py:625
    if function_call:
        yield [*new_messages, Message(role="function", function_call={..., "is_complete": False})]  # pending
        function_output, new_snippets = handle_function_call(...)
        yield [*new_messages, Message(role="function", function_call={..., "is_complete": True, "snippets": new_snippets})]
        user_message = f"<function_output>\n{function_output}\n</function_output>\n\n{function_response}"  # :708
    else:
        break

def postprocessed_stream(*args, **kwargs):           # :767
    previous_state = []
    try:
        for messages in stream_state(*args, **kwargs):
            current_state = [message.model_dump() for message in messages]
            patch = jsonpatch.JsonPatch.from_diff(previous_state, current_state)  # :775
            if patch:
                yield patch.to_string()
            previous_state = current_state
    except Exception as e:
        yield json.dumps([{"op": "error", "value": "ERROR\n\n" + str(e)}])      # :780-784 — IN-BAND failure
```

**Flow:** `chat_codebase` is a thin authenticated wrapper (empty-messages guard, client resolution, posthog metadata) that delegates to `chat_codebase_stream`; `use_openai` is derived purely from the model-name prefix (`gpt*`), so the same loop serves both providers. `stream_state` first yields the empty list (an initial empty patch primes the client), then runs at most 5 rounds: each round streams from the LLM with stop sequences on the function-call tags, withholds the first 50 chars (too short to contain a tag), and re-parses the accumulated prefix on EVERY token — the growing `analysis`/`user_response`/`self_critique` XML fields are re-extracted and re-yielded as fresh whole-list snapshots, so the UI renders live-typing messages by simply replacing its state. The XML-to-role mapping is fixed: analysis and self_critique become `function` messages (self_critique never sets is_complete), user_response becomes `assistant`. When the stream ends at a function-call stop tag, the raw string is normalized (`<function_calls>`→`<function_call>`, closing tag appended — the stop sequence consumed the closer), parsed by the SAME validator the modify agent uses, and surfaced in two phases: a pending `is_complete: False` function message, then after `handle_function_call` the completed message carrying `new_snippets` (search results flow back into UI context). The function output is fed back as `<function_output>` + the canned `function_response` prompt. A round with no parseable function call breaks the loop. After the loop, the FINAL assistant message is scanned for `<code_change>` blocks via `extract_objects_from_string` (per-tag regex; failed params are logged + posthog'd but partial results are still returned); pure additions to the same file (both `original_code == ""`) are merged by joining `new_code` with `"\n\n"` + lstrip; each suggestion becomes a real `FileChangeRequest` (change_type decided by `cloned_repo.get_contents` try/except — file exists ⇒ modify, else create) and is run through `get_error_message_dict` — the ticket plane's pre-validation — with each error written into `annotations[i]["error"]`. **The suggestions are validated but NEVER applied; state stays `"pending"`** — application is the user's click, not the server's job. `postprocessed_stream` wraps everything: per snapshot it diffs the previous model_dump list against the current one and yields only non-empty patches as strings; ANY exception anywhere in the pipeline becomes a single `[{"op": "error", ...}]` document — failure is IN-BAND as a patch op, never an HTTP error, because the response has already started streaming.
**Invariant:** The wire protocol is state-replacement, not append: every yield is a full message list, and the jsonpatch layer converts that into minimal deltas — the generator stays simple (rebuild everything) while the client stays efficient (apply diffs). The 5-round cap and the 50-char withholding are both load-bearing: the cap bounds cost per user message, and the threshold prevents parsing garbage prefixes that cannot yet contain a tag. Reusing `validate_and_parse_function_call` and `get_error_message_dict` from the ticket plane means chat suggestions are held to the exact same grammar and validation bar as agent edits — one validation code path, two consumers. The error-op convention means a client MUST handle an `op: "error"` patch as a terminal failure state. Coverage caveat: no offline unit test exists for chat/api.py at pin (tests/ holds live-API harness scripts); standing runner blocks unchanged.
**Probe:** Deterministic probes executed at pin: `grep -n 'stop_sequences=\[' sweepai/chat/api.py` → :575 only; `grep -n 'len(result_string) < 50'` → :588 only; `grep -n 'replace("<function_calls>"'` → :660 only; `grep -n 'from_diff'` → :775 only; `grep -n '"op": "error"'` → :782 only; `grep -n 'codeSuggestions'` → :726,:758; `grep -n 'for _ in range' sweepai/chat/api.py` → :571 (5 rounds) + :1089 (unrelated 60*6 loop in a different endpoint); `grep -rn 'get_error_message_dict(' sweepai --include=*.py | grep -v def` → modify.py:154 + chat/api.py:752 (two consumers); `grep -rn 'chat_codebase_stream(' | grep -v def` → api.py:418 only (single caller); `grep -rn 'extract_objects_from_string' --include=*.py` → defs str_utils.py:213 + callers chat/api.py:714, review_utils.py:750; `grep -rn 'At least one message is required\|No snippets were sent'` → :411/:464 (the two entry guards); `grep -n 'EXPAND_SIZE'` → :462 def + :475/:519 uses.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "sweep", query: "chat_codebase_stream postprocessed_stream jsonpatch from_diff codeSuggestions is_complete stop_sequences", limit: 10 });
// NOT executed this session (Codebase Memory MCP not connected); direct source reads of
// chat/api.py :401-433/:451-540/:554-790 + modify_utils.py:625-640/:1428-1433 + str_utils.py:213-224
// at pin substituted — see verification.md pass 7.
```

## Verdict
Adopt the snapshot-generator + jsonpatch-wrapper split (generators yield whole state; a thin wrapper diffs it — trivially testable layers), the pending→complete two-phase function-call surfacing (the UI can show "calling tool…" before results exist), in-band error ops once streaming has begun (HTTP status codes are useless mid-stream), the 50-char parse threshold, and validating-but-never-applying chat suggestions through the SAME pre-validation kernel the agent plane uses (one grammar, one error vocabulary, shared across surfaces). Adapt: re-parsing the full accumulated string on every token is O(n²) over long responses — debounce or parse incrementally; the `model.startswith("gpt")` provider switch is brittle if you add providers; the 5-round cap should be configurable. Omit: the posthog capture calls, the `EXPAND_SIZE = 100` snippet expansion constant (product-tuned), and the self_critique role mapping unless your prompt format emits it. Coverage caveat: no offline test at pin; this capsule shares its validation kernels with fcr-prevalidation-plane and search-replace-match-ladder — a grammar change in entities.py invalidates all three.

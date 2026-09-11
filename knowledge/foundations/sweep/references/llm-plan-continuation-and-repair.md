<!-- capsule-v2 -->
# LLM plan continuation & FCR repair — how do you survive truncated generations and invalid change-requests without restarting planning?

**Source:** sweep (Apache-2.0) `main@a8b8b67bda4f`; Codebase Memory `sweep`. **Question:** How do long structured plans get stitched across multiple LLM calls, and how are invalid FileChangeRequests patched by index?

## continuous_llm_calls continuation loop + 3-round get_error_message repair
**Path/Symbol:** `sweepai/core/chat.py:continuous_llm_calls` (:663–711); producer/consumer in `sweepai/core/sweep_bot.py:get_files_to_change` (:397–702, decisively :645–694); patch parser `parse_patch_fcrs` (:137–152).
**Signature:** `continuous_llm_calls(chat_gpt, *, stop_sequences=["</plan>"], MAX_CALLS=10, use_openai=False, response_cleanup=lambda x: x, **kwargs) -> str`.
**Data Shape:** Repair loop state: `(error_message, error_indices)` from validation; patches parse into `drops: list[int]` and `matches: list[(index, FileChangeRequest)]`.

### Decisive source
```python
while not any(token in response for token in stop_sequences) \
    and len(next_response) > 3.5 * 4096 * 0.8 \
    and num_calls < MAX_CALLS:
    last_line_index = response.rfind("\n")
    response = response[:last_line_index].rstrip()
    last_k_lines = response.split("\n")[-10:]
    content = ("Continue generating. DO NOT restart from scratch. "
               "Here is the last part of your response to continue from:\n\n" + "\n".join(last_k_lines))
    chat_gpt.messages[-1].content = response_cleanup(response)
    ...
    response += next_response                      # CONCATENATE, never replace

# sweep_bot.py:653-690 — index-keyed repair:
for error_resolution_count in range(3):
    if not error_message: break
    fix_attempt = continuous_llm_calls(chat_gpt, content=fix_files_to_change_prompt.format(
        error_message=error_message, allowed_indices=english_join(...)), ...)
    drops, matches = parse_patch_fcrs(fix_attempt)
    for index, new_fcr in matches:
        if "COPIED_FROM_PREVIOUS_MODIFY" in new_fcr.instructions:
            file_change_requests[error_indices[index]].filename = renames_dict.get(new_fcr.filename, ...)
            continue
        file_change_requests[error_indices[index]] = new_fcr
    for drop in sorted(drops, reverse=True):       # reverse ⇒ earlier indices stay valid
        file_change_requests.pop(error_indices[drop])
```

**Flow:** planning runs renames → numbered sub-requests → issue analysis → plan, each stage a `continuous_llm_calls` bounded at 10 calls with its own stop token (`</issue_sub_requests>`, `</issue_analysis>`, `</plan>`). A response continues only while its stop token is missing AND it is long enough to plausibly be cut mid-thought; the tail is truncated to the last newline and the model is re-prompted with the final 10 lines; outputs are string-concatenated. After parsing `FileChangeRequest._regex` matches, path validation yields error indices; up to three rounds let the model rewrite (by index) or `<drop>N</drop>` offending requests, with renames applied to repaired filenames. `RegexMatchError` escapes the whole block to a degenerate `return [], ""`.
**Invariant:** Continuation MUTATES `messages[-1]` through `response_cleanup` before re-asking, so the next call sees cleaned context — but a failed continuation call is swallowed (logged) keeping partial output rather than raising. In repair, drops MUST be applied in descending index order or every subsequent `error_indices[i]` points past the wrong element. `COPIED_FROM_PREVIOUS_MODIFY` patches are filename-only overrides, not instruction replacements.
**Probe:** No offline unit test for either mechanism (LLM-dependent — coverage caveat). Deterministic probes at pin: `grep -c 'MAX_CALLS' sweepai/core/chat.py` → 2; `grep -n 'sorted(drops, reverse=True)' sweepai/core/sweep_bot.py` → :686.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "sweep", query: "get files to change stream file change requests repair error", limit: 10 });
// executed at pin: get_files_to_change sweep_bot.py 398-702 (#1),
// get_files_to_change_for_on_comment :705-1018 shares the same machinery,
// parse_patch_fcrs :137-152, continuous_llm_calls chat.py 663-711
```

## Verdict
Adopt stop-token-bounded concatenating continuation with tail-truncated resume prompts and cleanup-mutated history, plus index-addressed FCR repair with descending-order drops and filename-only copy semantics. Adapt stop tokens/prompts to your schema. Omit OpenAI-specific `<original_code>` truncation anchoring unless you port that provider path too.

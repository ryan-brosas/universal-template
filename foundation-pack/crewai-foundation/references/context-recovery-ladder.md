<!-- capsule-v2 -->
# Context-window recovery ladder — how does the executor survive context-length errors, and what does summarization preserve?

**Source:** crewAI MIT `main@f4731f5025f861c78e3af0487cc80bf5e7c64782`; Codebase Memory `ext-crewAI`. **Question:** How is a provider context error detected, and what exactly does in-place message summarization keep vs drop?

## is_context_length_exceeded / handle_context_length / summarize_messages
**Path/Symbol:** `lib/crewai/src/crewai/utilities/agent_utils.py:781-792` (`is_context_length_exceeded`), `:795-832` (`handle_context_length`), `:1048-1131` (`summarize_messages`); chunking helpers `:835-992`.
**Signature:** `def handle_context_length(respect_context_window: bool, printer, messages, llm, callbacks, verbose=True) -> None  # raises SystemExit when not respecting`.
**Data Shape:** Token estimate = `len(text) // 4` (conservative cross-provider heuristic); chunk budget from `llm.get_context_window_size()`.

### Decisive source
```python
# detection — substring classification via LLMContextLengthExceededError helper:
return LLMContextLengthExceededException(str(exception))._is_context_limit_error(
    str(exception))

if respect_context_window:
    summarize_messages(messages=messages, llm=llm, ...)   # mutate IN PLACE
else:
    raise SystemExit("Context length exceeded and user opted not to summarize. ...")

# summarize_messages preservation rules:
preserved_files = {…for user msgs with "files"…}      # re-attached to summary
system_messages   = [m for m in messages if m.get("role") == "system"]
non_system        = [m for m in messages if m.get("role") != "system"]
chunks = _split_messages_into_chunks(non_system, max_tokens)
# oversized single messages split into "[Part i/n]" sub-messages FIRST
# (body budget = max_tokens - 5 for the prefix); chunks summarized in PARALLEL
# via asyncio.gather when >1; each summary extracted from <summary>…</summary>
messages.clear()
messages.extend(system_messages)                      # system messages VERBATIM
messages.append(summary_message_with_files)           # then ONE merged summary
```

**Flow:** Any LLM exception on the ReAct/native path → litellm-module exceptions re-raised untouched (`e.__class__.__module__.startswith("litellm")`) → else classify → context-error routes to `recover_from_context_length` which calls `handle_context_length`, increments iterations, and returns `"initialized"` so the SAME flow continues with compacted history. Summary formatting keeps role labels `[ASSISTANT]:`/`[TOOL_RESULT (name)]:`/`[USER]:`, renders tool-call-only assistant messages as `[Called tools: a, b]`, and multimodal blocks as their text parts or `[multimodal content]`.
**Invariant:** Summarization MUTATES the caller's list in place (the executor's state.messages IS the loop's history) while preserving: all system messages verbatim and first, files attached to any user message (merged onto the final summary message). Dropping either silently degrades agent persona or breaks multimodal follow-ups. The SystemExit branch is a deliberate hard stop, not an error path to catch.
**Probe:** `tests/agents/test_agent.py::test_handle_context_length_exceeds_limit` and `test_handle_context_length_exceeds_limit_cli_no`; executor routing pinned by `TestCallLLM.test_call_llm_context_error`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-crewAI", query: "summarize_messages handle_context_length", limit: 5, detail: "ids" });
```

## Verdict
Adopt detect→summarize-or-stop with verbatim-system + preserved-files semantics; adapt the token heuristic if you have a real tokenizer; omit parallel chunk summarization below ~10 chunks (single-threaded loop is simpler and equivalent there).

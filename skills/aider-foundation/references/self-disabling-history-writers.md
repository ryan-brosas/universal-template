<!-- capsule-v2 -->
# Self-disabling session writers — how does append-only transcript logging fail without ever failing the session?

**Source:** Aider Apache-2.0 `main@5dc9490bb35f9729ef2c95d00a19ccd30c26339c`; Codebase Memory project `aider`. **Question:** When the chat-history file becomes unwritable mid-session, how do you keep the REPL alive and stop retrying — and what grammar must writers share with the reader that replays sessions?

## Append-only writers that normalize one markdown grammar, then silence themselves on first failure
**Path/Symbol:** `aider/io.py`: `log_llm_history` (:754-765), `user_input` (:775-789), `ai_output` (:793-795), `append_chat_history` (:1117-1136). Fan-in (trace inbound depth 1): callers_total=**8** — `InputOutput.__init__` (banner), `_tool_message`, `ai_output`, `confirm_ask`, `prompt_ask`, `tool_output`, `user_input`, plus `benchmark.run_test_real`; every transcript surface converges on ONE writer.
**Signature:** `append_chat_history(text, linebreak=False, blockquote=False, strip=True)`; `user_input(inp, log_only=True)`; `ai_output(content)`; `log_llm_history(role, content)`.
**Data Shape:** chat history = markdown lines; user turns are `#### ` headings whose wrapped lines join with `"  \n"` (markdown hard break); blank input becomes `<blank>`; assistant turns get blank-line padding; llm-history = `ROLE <isoformat-seconds>\n<content>\n`.

### Decisive source
```python
if blockquote:
    if strip: text = text.strip()
    text = "> " + text                    # :1118-1121 blockquote normalization
if linebreak:
    if strip: text = text.rstrip()
    text = text + "  \n"                  # :1122-1125 hard-break token the splitter consumes
if not text.endswith("\n"):
    text += "\n"
if self.chat_history_file is not None:
    try:
        self.chat_history_file.parent.mkdir(parents=True, exist_ok=True)
        with self.chat_history_file.open("a", encoding=self.encoding, errors="ignore") as f:
            f.write(text)
    except (PermissionError, OSError) as err:
        print(f"Warning: Unable to write to chat history file {self.chat_history_file}.")
        print(err)
        self.chat_history_file = None     # :1136 KILL-SWITCH — session continues, logging stops
```

```python
except (PermissionError, OSError) as err:
    self.tool_warning(f"Unable to write to llm history file {self.llm_history_file}: {err}")
    self.llm_history_file = None          # :763-765 same pattern for the LLM log
```

**Flow:** every user/assistant/tool/confirm/prompt/banner surface funnels into `append_chat_history`, which normalizes the blockquote prefix, appends the two-space hard-break when `linebreak=True`, guarantees a trailing newline, then opens in append mode with `errors="ignore"`. The FIRST PermissionError/OSError prints a warning once and nulls the file attribute — subsequent calls short-circuit on the None guard instead of re-attempting or raising. `user_input` encodes each turn as a `####` heading with two-space continuation joins (`"<blank>"` for empty input); `log_only=False` ALSO echoes via `display_user_input` (this is confirm_ask's group-replay echo). Writer and reader share one implicit grammar with history-markdown-splitter's `#### `/`> ` parser — change either side and session replay silently corrupts.
**Invariant:** logging is strictly best-effort — no history failure can kill the REPL or lose a chat turn; degradation is one warning, not per-turn noise; the markdown grammar is a cross-module contract, not an implementation detail. Caveats: these writers have NO dedicated upstream tests (anchor-verified only); `errors="ignore"` means hostile bytes vanish silently rather than failing the encode.
**Probe:** anchors :1118-1136/:763-765 byte-checked against served snippets this run; executed `.venv/bin/python -m pytest tests/basic/test_io.py -k 'autocompleter or confirm_ask' -q` → **7 passed, 16 deselected** (the confirm_ask suites exercise append_chat_history indirectly through group-replay paths).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "aider", query: "append_chat_history", limit: 3 });
// rank-1 total:1: aider.aider.io.InputOutput.append_chat_history aider/io.py 1117-1136 (-24.6)
await mcp.codebase_memory.trace_path({ project: "aider", function_name: "append_chat_history", direction: "inbound", depth: 1 });
// callers_total: 8 — __init__, _tool_message, ai_output, confirm_ask, prompt_ask, tool_output, user_input, benchmark.run_test_real
```

## Verdict
Adopt the self-disabling writer pattern for any best-effort durable log: normalize the record grammar at ONE choke point, guard writes behind a nullable handle, and convert the first write failure into a single warning plus permanent disable. Adapt the grammar to your replay format but keep writer/reader as one contract. Omit nothing — the kill-switch, not the try/except, is the reusable idea.

<!-- capsule-v2 -->
# Chat-history markdown splitter — `#### `/`> ` role markers rebuild a replayable message list

**Source:** Aider Apache-2.0 `main@5dc9490bb35f9729ef2c95d00a19ccd30c26339c`; Codebase Memory project `aider` (full index). **Question:** How do you turn aider's exported chat markdown back into structured messages so a session can be restored or analyzed?

## Marker grammar
**Path/Symbol:** `aider/utils.py`: `split_chat_history_markdown(text, include_tool=False)` (:148), local `append_msg(role, lines)` (:155).
**Signature:** `-> list[dict(role, content)]`; blank/whitespace-only runs never become messages.
**Data Shape:** `# ` heading lines are dropped entirely (title noise); `#### ` marks the start of a USER turn (`line[5:]` is first content); `> ` prefixes TOOL output; every other line continues the current ASSISTANT run.

### Decisive source
```python
for line in lines:
    if line.startswith("# "):
        continue                       # title line: discarded
    if line.startswith("> "):
        append_msg("assistant", assistant); assistant = []
        append_msg("user", user); user = []
        tool.append(line[2:])          # tool output closes both open turns
        continue
    if line.startswith("#### "):
        append_msg("assistant", assistant); assistant = []
        append_msg("tool", tool); tool = []
        content = line[5:]             # new user turn begins
        user.append(content)
        continue
    append_msg("user", user); user = []
    append_msg("tool", tool); tool = []
    assistant.append(line)             # default: assistant prose
```

**Flow:** single pass accumulating per-role buffers; any role-flush closes ALL other pending buffers first (order preserved); trailing buffers flushed at EOF; `include_tool=False` filters tool dicts out of the result.
**Invariant:** flush-before-accumulate keeps interleaved roles in original order even when markers alternate rapidly; empty buffers produce no phantom messages (`if lines.strip()` guard inside append_msg).
**Probe:** no upstream direct test (only fixture files reference it) → executed this run: `.pi/work/foundations-deep-farm/scratch-aider-pass2/probe_gate5.py::history-split-roles` (role sequence + tool filter verified on a mixed transcript), repo venv GREEN.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "aider", name_pattern: "split_chat_history_markdown", limit: 5 });
```

## Verdict
Adopt the marker grammar + ordered flush discipline for chat-log round-tripping; adapt marker spellings to your export format; omit `format_messages`/`show_messages` debug printers in the same file. Coverage caveat: probe-pinned only.

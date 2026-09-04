<!-- capsule-v2 -->
# Multimodal file injection — how do crew/task files and inputs reach the model as real attachments on the last user message?

**Source:** crewAI MIT `main@f4731f5025f861c78e3af0487cc80bf5e7c64782`; Codebase Memory `ext-crewAI`. **Question:** How are files merged from store + inputs, attached to WHICH message, and what survives summarization?

## _inject_multimodal_files / _inject_files_from_inputs
**Path/Symbol:** `lib/crewai/src/crewai/experimental/agent_executor.py:3152-3197` (`_inject_files_from_inputs` / `_ainject…`); deprecated-twin reference `agents/crew_agent_executor.py:249-307` (`_inject_multimodal_files`); file store `utilities/file_store.py` (`get_all_files` / `aget_all_files`).
**Signature:** `def _inject_files_from_inputs(self, inputs: dict | None) -> None`.
**Data Shape:** `files: dict[str, Any]` merged crew/task-store first, inputs second ("Input files take precedence over crew/task files with the same name"); attached as `msg["files"] = files` on the LAST user-role message.

### Decisive source
```python
# deprecated executor twin (identical logic, clearest docstring):
files: dict[str, Any] = {}
if self.crew and self.task:
    crew_files = get_all_files(self.crew.id, self.task.id)
    if crew_files:
        files.update(crew_files)          # store first…
if inputs and inputs.get("files"):
    files.update(inputs["files"])         # …inputs override by filename
if not files:
    return
for i in range(len(self.messages) - 1, -1, -1):   # reverse scan
    msg = self.messages[i]
    if msg.get("role") == "user":
        msg["files"] = files               # attach to the LAST user message
        break
```

**Flow:** invoke → after `_setup_messages`, before the loop → merge → reverse-scan for last user message → mutate in place. The LLM layer later expands `msg["files"]` into provider image/document blocks. On context-window recovery, `summarize_messages` collects every user message's files BEFORE clearing and re-attaches the union to the synthesized summary message — attachments survive compaction.
**Invariant:** Attachment target is the LAST user message (the one immediately preceding tool iterations), never the system prompt; precedence is input-over-store so a caller can substitute a corrected file without mutating the crew's store; async path uses `aget_all_files` (store may be remote) but identical merge order.
**Probe:** `tests/agents/test_agent_executor.py::test_inject_files_from_crew_task_store` (pins merge + override), `test_ainject_files_from_crew_task_store_uses_async_store`; preservation pinned inside summarize tests at `tests/agents/test_agent.py::test_handle_context_length_exceeds_limit`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-crewAI", query: "inject multimodal files get_all_files", limit: 6, detail: "ids" });
```

## Verdict
Adopt store-then-inputs merge with last-user-message attachment; adapt to your attachment schema (dict name→bytes is crewAI's shape); omit nothing — the summarization interplay is the part porters always miss.

<!-- capsule-v2 -->
# Role-playing worker turn loop — How does a two-agent dialogue become one task result?

**Source:** CAMEL-AI/camel Apache-2.0 `master@13dc7a7d`; Codebase Memory `ext-camel`. **Question:** What are the loop bounds, termination signals, and summarizer fallbacks that convert a RolePlaying session into a TaskState?

## Bounded astep loop + sentinel string + structured summarize
**Path/Symbol:** `camel/societies/workforce/role_playing_worker.py:RolePlayingWorker._process_task` (:107-261).
**Signature:** `_process_task(task, dependencies, stream_callback=None) -> TaskState`; constructor takes `chat_turn_limit: int = 20` plus assistant/user/summarizer agent kwargs.
**Data Shape:** `RolePlaying` society per task; `chat_history: List[str]` of "AI User:/AI Assistant:" lines; outcome via `TaskResult{content, failed}` schema.

### Decisive source
```python
while n < self.chat_turn_limit:
    n += 1
    assistant_response, user_response = await role_play_session.astep(input_msg)
    if assistant_response.terminated:
        reason = assistant_response.info['termination_reasons']; break
    if user_response.terminated:
        ...; break
    ...
    chat_history.append(f"AI User: {user_response.msg.content}")
    ...
    if "CAMEL_TASK_DONE" in user_response.msg.content:
        break
    input_msg = assistant_response.msg
```

**Flow:** build ROLEPLAY_PROCESS_TASK_PROMPT (task content + parent content + `dependency_tasks_info` = "id/content/result" lines from `Worker._get_dep_tasks_info`, worker.py :83-91) → fresh `RolePlaying(with_task_specify=False)` per task → alternate `astep` until ANY of: assistant terminated, AI-user terminated, `"CAMEL_TASK_DONE"` sentinel appears in the USER's message, or turn budget exhausts → join history → ROLEPLAY_SUMMARIZE_PROMPT into the dedicated Summarizer agent → structured parse; handler-path falls back to `TaskResult(content="Task summarization failed", failed=True)` on unparseable output, native-path checks `response.msg.parsed is None` the same way → set `task.result`, then the shared `is_task_result_insufficient(task)` veto decides DONE vs FAILED (:253-258).
**Invariant:** The turn limit and BOTH terminated flags are the only guaranteed exits — the sentinel is cooperative and can be missed; summarization ALWAYS runs even when the loop exits by timeout, so a task result exists for every posted task.
**Probe:** `grep -c 'CAMEL_TASK_DONE' camel/societies/workforce/role_playing_worker.py` → 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-camel", query: "RolePlayingWorker _process_task chat_turn_limit CAMEL_TASK_DONE summarize", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt multi-exit bounded dialogue + always-summarize for debate-style workers. Adapt sentinel vocabulary. Omit kwargs pass-through config surface.

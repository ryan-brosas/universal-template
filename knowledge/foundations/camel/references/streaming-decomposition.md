<!-- capsule-v2 -->
# Streaming decomposition — How do you surface subtasks incrementally while a model is still emitting the plan?

**Source:** CAMEL-AI/camel Apache-2.0 `master@13dc7a7d`; Codebase Memory `ext-camel`. **Question:** What is the delta-vs-accumulate handling and partial-parse contract that yields finished `<task>` blocks early without corrupting the final list?

## Accumulate → reparse-complete-blocks → yield-new-tail
**Path/Symbol:** `camel/tasks/task.py:Task._decompose_streaming` (:460-529), `_parse_partial_tasks` (:550-577), sync twin `_decompose_non_streaming` (:531-548).
**Signature:** `decompose(agent, prompt=None, task_parser=parse_response, stream_callback=None) -> Union[List[Task], Generator[List[Task], None, None]]` — generator iff response is streaming (`is_streaming_response`).
**Data Shape:** Emits batches of Tasks with ids `{parent_id}.{i}`; chunk mode read from `chunk.info["stream_accumulate_mode"]` (`"delta"` appends, else chunk holds full text so far).

### Decisive source
```python
if stream_accumulate_mode == "delta":
    accumulated_content += chunk.msg.content
else:
    accumulated_content = chunk.msg.content      # accumulate mode
...
current_tasks = self._parse_partial_tasks(accumulated_content)
if len(current_tasks) > yielded_count:
    new_tasks = current_tasks[yielded_count:]
    ...
    yield new_tasks; yielded_count = len(current_tasks)
```

**Flow:** per chunk: update accumulated text by mode → invoke stream_callback inside try/except (callback failures only warn) → regex-reparse ALL complete `<task>(.*?)</task>` blocks (DOTALL) over the whole accumulation → validate each candidate through `validate_task_content`, skipping invalid ones with a warning → yield only tasks beyond the high-water mark. After the stream ends, a FINAL authoritative parse via `task_parser` REPLACES `self.subtasks`, and every task gets `additional_info = parent.additional_info` + `parent = self`. Parse errors mid-stream are swallowed (`continue`) because later chunks complete the blocks.
**Invariant:** Streaming yields are previews; `self.subtasks` is set ONLY from the final parse — downstream code must not treat yielded tasks as durable. The monotonic `yielded_count` cursor makes re-parsing idempotent.
**Probe:** `grep -c 'stream_accumulate_mode' camel/tasks/task.py` → 4.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-camel", query: "_decompose_streaming _parse_partial_tasks yielded_count", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt full-text-reparse + high-water-yield for any incremental structured extraction. Adapt block delimiters to your schema tags. Omit the callback plumbing if you don't stream to UIs.

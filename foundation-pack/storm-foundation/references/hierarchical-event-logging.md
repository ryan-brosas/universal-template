<!-- capsule-v2 -->
# Hierarchical event logging — how do you capture per-stage time/usage trees with a strict stack discipline?

**Source:** storm MIT `main@fb951af7`; Codebase Memory `storm`. **Question:** What are the state rules of a nested event logger that must survive concurrent pipeline stages without corrupting timing?

## Connected graph-selected seam
**Path/Symbol:** `knowledge_storm/logging_wrapper.py:LoggingWrapper` (:55-212) + `EventLog` (:10-52).
**Signature:** `log_pipeline_stage(pipeline_stage)` and `log_event(event_name)` contextmanagers; `add_query_count(count)`; `dump_logging_and_reset(reset_logging=True)`.
**Data Shape:** `logging_dict[stage] = {time_usage: {event→EventLog}, lm_usage, lm_history, query_count, total_wall_time}`; events nest via `child_events` dict; times stored UTC, rendered America/Los_Angeles with millisecond truncation (`strftime(...)[:-3]`).

### Decisive source
```python
@contextmanager
def log_pipeline_stage(self, pipeline_stage):
    if self.pipeline_stage_active:
        print("A pipeline stage is already active, ending the current stage safely.")
        self._pipeline_stage_end()            # defensive auto-close instead of raise
    start_time = time.time()
    try:
        self._pipeline_stage_start(pipeline_stage)
        yield
    except Exception as e:
        print(f"Error occurred during pipeline stage '{pipeline_stage}': {e}")
        # swallow: stage failure must not kill the run loop
    finally:
        self.logging_dict[self.current_pipeline_stage]["total_wall_time"] = time.time() - start_time
        self._pipeline_stage_end()            # drains lm_usage + lm_history HERE

# event nesting: top-level events keyed in time_usage (re-started if reused),
# nested events live under parent.child_events; stack pop only when names match
if current_event_log.event_name == event_name:
    self.event_stack.pop()
```

**Flow:** Stage opens a fresh bucket → events push/pop an explicit stack (top-level events may be RE-entered — their EventLog just gets a new start time) → at close, `_pipeline_stage_end()` collects `lm_config.collect_and_reset_lm_usage()/lm_history()` so usage attribution aligns exactly with the open window → dump renders seconds + formatted timestamps.
**Invariant:** (1) Only ONE active stage at a time; re-entry auto-closes the previous stage rather than raising. (2) `_event_start/_event_end` RAISE on misuse (no stage / no parent / unknown event) — the lax path exists only at stage level. (3) LM usage/history MUST be drained inside the stage-close, never later, or cross-stage contamination follows. (4) Same-named sibling events under one parent collapse into one EventLog (dict-keyed), so repeated event names within a stage overwrite.
**Probe:** deterministic pin GREEN — graph resolves `LoggingWrapper.log_pipeline_stage` (:173-190) and `_event_start` (:78-114) line-exact; fan-in 18 confirms it as the Co-STORM hot seam.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "storm", query: "LoggingWrapper log_pipeline_stage event stack", limit: 10 });
```

## Verdict
Adopt the stage-bucket + event-stack + drain-on-close design for pipeline observability; adapt the swallow-vs-raise split to your error policy; omit the California-timezone rendering outside US-facing UIs. Caveat: no upstream tests; source-pinned.

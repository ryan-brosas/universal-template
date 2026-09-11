<!-- capsule-v2 -->
# Workflow memory accumulation — How does a pooled, reset-every-task agent still preserve a full conversation record for later reuse?

**Source:** CAMEL-AI/camel Apache-2.0 `master@13dc7a7d`; Codebase Memory `ext-camel`. **Question:** What is the accumulator transfer pattern that survives agent pooling and resets?

## Side-channel accumulator + lazy WorkflowMemoryManager
**Path/Symbol:** `camel/societies/workforce/single_agent_worker.py:_get_conversation_accumulator` (:325-332), memory transfer in `_process_task` (:479-501), `_get_workflow_manager` (:334-347).
**Signature:** `worker_agent.memory.retrieve() -> List[MemoryRecord]`; `accumulator.memory.write_records(records)`; manager `save_workflow(conversation_accumulator)` / `save_workflow_async`.
**Data Shape:** `_conversation_accumulator: Optional[ChatAgent]` — a `clone(with_memory=False)` of the base worker created ONCE lazily; per-attempt working agents are pool clones whose memories are wiped on handout.

### Decisive source
```python
if self.enable_workflow_memory:
    accumulator = self._get_conversation_accumulator()
    try:
        work_records = worker_agent.memory.retrieve()
        memory_records = [record.memory_record for record in work_records]
        accumulator.memory.write_records(memory_records)
    except Exception as e:
        logger.warning(f"Failed to transfer conversation to accumulator: {e}")
```

**Flow:** after each attempt (inside try, before finally returns the clone to the pool) copy the working clone's whole memory into the accumulator; failures only warn — telemetry must never break task processing. Save path (`save_workflow_memories_async`) delegates to WorkflowMemoryManager which summarizes via the BASE worker (asummarize for parallelism), writes markdown under session dirs keyed by role/title with generic-name fallback (`is_generic_role_name` frozenset {assistant, agent, user, system, worker, helper}, utils.py :22-24), then NULLS the accumulator after success (:694-703) so the next save starts from a clean slate. Load path uses agent-driven smart selection over saved workflow metadata (title/description/tags) capped by `max_workflows` (default 3).
**Invariant:** Accumulation is ADDITIVE across attempts while pooling is RESET-per-borrow — conflating them either loses history or poisons fresh tasks. The accumulator is cleared exactly once per successful save.
**Probe:** `grep -c 'write_records' camel/societies/workforce/single_agent_worker.py` → 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-camel", query: "conversation_accumulator write_records retrieve workflow memory", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt side-channel accumulation whenever pooled instances need durable transcripts. Adapt storage format. Omit smart-selection LLM scoring if you have simpler retrieval.

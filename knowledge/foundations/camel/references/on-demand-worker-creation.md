<!-- capsule-v2 -->
# On-demand worker creation with structured fallbacks — How do you mint a brand-new specialist agent from an LLM's spec without trusting the LLM?

**Source:** CAMEL-AI/camel Apache-2.0 `master@13dc7a7d`; Codebase Memory `ext-camel`. **Question:** What is the parse-fallback chain that turns a coordinator response into a valid WorkerConf, and what does CREATE_WORKER recovery do with it?

## Prompted schema + tiered defaults, never a raise
**Path/Symbol:** `camel/societies/workforce/workforce.py:Workforce._create_worker_node_for_task` (:4186-4332), `_create_new_agent` (:4334).
**Signature:** `async def _create_worker_node_for_task(self, task: Task) -> Worker`; schema `WorkerConf{role, sys_msg, description}` (utils.py :114-126).
**Data Shape:** CREATE_NODE_PROMPT filled with task content + `_get_child_nodes_info()` + additional_info; two parsing regimes behind `use_structured_output_handler` (default True).

### Decisive source
```python
if response.msg is None or response_content is None:
    logger.error("Coordinator agent returned empty response for worker creation")
    new_node_conf = WorkerConf(
        description=f"Fallback worker for task: {task.content}",
        role="General Assistant",
        sys_msg="You are a general assistant that can help with various tasks.",
    )
else:
    result = self.structured_handler.parse_structured_response(
        response_content, schema=WorkerConf,
        fallback_values={"description": f"Worker for task: {task.content}",
                         "role": "Task Specialist",
                         "sys_msg": f"You are a specialist for: {task.content}"})
```

**Flow:** prompt the coordinator → handler path: `generate_structured_prompt` (schema + example) then `parse_structured_response` which returns a WorkerConf instance, a dict to be splatted (`WorkerConf(**result)`), or built-in fallback values on garbage; native path: `response_format=WorkerConf` then json.loads with a RuntimeError ONLY for malformed JSON — but empty responses STILL take the General-Assistant fallback → compatibility gate `_validate_agent_compatibility(new_agent, ...)` before wiring → new node appended to children and returned; caller (`_apply_recovery_strategy` CREATE_WORKER branch :2010-2016) posts the failed task straight to `assignee.node_id`. The same degrade-not-crash philosophy appears in assignment parsing (`fallback_values={"assignments": []}`, :3847).
**Invariant:** Worker creation can fail into a GENERIC worker but never fails the recovery — the only hard error is native-path malformed JSON, and even that raises AFTER logging full response content. Every created agent passes the same compatibility validation as user-provided ones.
**Probe:** `grep -c 'Fallback worker for task' camel/societies/workforce/workforce.py` → 2.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-camel", query: "_create_worker_node_for_task WorkerConf parse_structured_response fallback", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt LLM-spec'd provisioning with typed fallback configs. Adapt WorkerConf fields and the generic-worker persona. Omit dual parsing paths if your host guarantees structured output.

<!-- capsule-v2 -->
# SaveReuse trajectory consolidation — replay the run's code steps into one reusable artifact

**Source:** cuga-agent Apache-2.0 `main@5de53ade`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** After an agent completes a task as a sequence of generated code blocks, how do you turn that trajectory into ONE reusable script — reading from the live in-memory step tracker when present, falling back to on-disk files, and never letting consolidation failure break the user-facing answer?

## The consolidator
**Path/Symbol:** `src/cuga/backend/cuga_graph/nodes/save_reuse/save_reuse_agent/utils/save_reuse.py` (`get_python_content_from_trajectory` :15-24, `read_python_files` :27-42, `consolidate_flow` :45-73); `save_reuse_node.py` (`SaveReuseNode.node_handler` :30-39).
**Signature:** `async consolidate_flow(chain, user_intent, file_pattern="f*.py", dynamic=True) -> AIMessage | None`.
**Data Shape:** files dict `{"f1.py": <code>, "f2.py": ...}` — keys are ordinal, order = execution order; prompt input is `{files_section, user_intent}`.

### Decisive source
```python
# save_reuse.py:18-23 — the source of truth is the TRACKER's CodeAgent steps,
# not a re-render of state history
for step in tracker.steps:
    if step.name == "CodeAgent":
        content = json.loads(step.data)
        code = content['code']
        files[f"f{indx}.py"] = code
        indx += 1

# save_reuse.py:71-73 — failure degrades to None, never raises
except Exception as e:
    logger.error(f"Error generating consolidation response: {e}")
    return None
```

**Flow:** dynamic mode pulls each recorded CodeAgent step's code out of the ActivityTracker (ordinal-named so execution order survives dict ordering); static mode reads `f*.py` from disk instead. Files render into one fenced `## f{n}.py` section per block, sent with the original user intent through the consolidation chain. The node wrapper runs the ReuseAgent with the pending HITL utterance appended (`"Or {hitl_response.text_response}"`), clears `hitl_response`, sets `final_answer`, and Commands to FinalAnswerAgent — the answer the user sees NEVER depends on consolidation succeeding.
**Invariant:** the trajectory source is the step tracker (what actually ran), not message re-parsing; empty trajectories return None early ("no CodeAgent steps") rather than prompting the LLM with nothing; every failure path logs and returns None — consolidation is a best-effort enhancement layered AFTER the completed run, so it can't corrupt the finished result.

**Probe:** direct tests: none target this module (the node is a thin Command hop and the utils are LLM-gated). Coverage caveat recorded — port against `get_python_content_from_trajectory`'s step shape `{name:"CodeAgent", data:json with 'code'}` and verify manually. Nearest behavioral pins are the plan-controller prompt tests that exercise the same ActivityTracker step rendering.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "consolidate_flow get_python_content_from_trajectory SaveReuseNode ReuseAgent", limit: 10 });
```

## Verdict
Adopt tracker-sourced (not re-derived) trajectory capture with ordinal naming, dual dynamic/static file sources, and strictly best-effort consolidation that can never degrade a completed run's answer. Adapt the step-name filter and prompt shape to your tracker schema. Omit the HITL utterance plumbing if your reuse flow has no approval gate.

<!-- capsule-v2 -->
# GatherEvidence agent tool — how does an agent gather evidence for a sub-question without corrupting the session question?

**Source:** paper-qa Apache-2.0 `main@57e89f72`; Codebase Memory `paper-qa`. **Question:** When an agent tool needs evidence for a MORE SPECIFIC question than the session's, how is the question swapped, guarded, and projected back?

## Connected graph-selected seam
**Path/Symbol:** `src/paperqa/agents/tools.py:GatherEvidence.gather_evidence` (:225-311).
**Signature:** `async def gather_evidence(self, question: str, state: EnvironmentState) -> str`.
**Data Shape:** Mutates `state.session` (PQASession) in place; returns a human-readable observation string (`"Added {delta} pieces of evidence.{best_evidence}\n\n" + status`). Class exposes `CONCURRENCY_SAFE` flag consumed by the tool-loop status protocol capsule.

### Decisive source
```python
if not state.docs.docs:
    raise EmptyDocsError("Not gathering evidence due to having no papers.")
...
original_question = state.session.question
l1 = l0 = len(state.session.contexts)
try:
    # Swap out the question with the more specific question
    # TODO: remove this swap, as it prevents us from supporting parallel calls
    state.session.question = question
    state.session = await state.docs.aget_evidence(query=state.session, ...)
    l1 = len(state.session.contexts)
finally:
    state.session.question = original_question
...
sorted_contexts = sorted(
    (c for c in state.session.contexts if c.question is None or c.question == question),
    key=lambda x: x.score, reverse=True)
top_contexts = "\n\n".join(f"- {sc.context}"
    for sc in sorted_contexts[: self.settings.agent.agent_evidence_n])
```

**Flow:** empty-docs rejection BEFORE any work → optional `{tool}_initialized` callbacks → try/finally question swap so aget_evidence scores chunks against the SUB-question while the session keeps its original question → per-question projection: only contexts tagged with that question (or untagged) are shown, top `agent_evidence_n` by score → `{tool}_completed` callbacks → delta-count observation. Contexts created during the swap are permanently stamped with the sub-question (Context.question), which is exactly what grouped rendering later keys on.
**Invariant:** The session question is ALWAYS restored in `finally`, even on failure — but because the swap is shared-state mutation, self-parallel calls are UNSAFE by construction (upstream TODO); callers must serialize this tool against itself even when it is marked concurrency-safe versus other tools.
**Probe:** `tests/test_agents.py::test_gather_evidence_rejects_empty_docs` (:562-614) pins that with empty Docs the tool raises and the agent loops to TRUNCATED rather than crashing the run. Deterministic source/test-range probe (no runner provisioned).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "paper-qa", query: "gather_evidence EmptyDocsError agent_evidence_n", limit: 10 });
// trace_path --project paper-qa --function-name gather_evidence --direction inbound → GatherEvidence.gather_evidence tool surface
```

## Verdict
Adopt the finally-guarded question-swap pattern plus per-question context stamping/projection and the delta-count observation format; adapt the callback hook names to your agent framework; omit the in-place session mutation in favor of passing the sub-question explicitly IF your runtime supports parallel tool calls — otherwise keep the serialization contract explicit. Coverage: agents/tools.py no_recorded_issue + metadata_match @ gen 2026-08-25T19:57:59Z.

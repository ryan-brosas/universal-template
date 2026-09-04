<!-- capsule-v2 -->
# Pending-input admission split — when is staged user input committed vs kept pending?

**Source:** OpenAI Agents Python MIT `main@cb8a2e7e`; Codebase Memory project `openai-agents-python`. **Question:** How does the runner admit mid-run user input so a server-managed conversation never persists input the provider rejected?

## Admission + server commit
**Path/Symbol:** `src/agents/run_internal/session_persistence.py:` `admit_pending_input` (:85–120), `commit_server_pending_input` (:123–186); streamed call sites at run_loop.py :1379–1433 (admission) and `_commit_pending_server_response` (:986–1005).
**Signature:** `async def admit_pending_input(*, run_state, agent, session, server_conversation_tracker, store, wrapper) -> list[RunItem]`; `def commit_server_pending_input(*, run_state, tracker, admission_items, generated_items, session_items, model_response, processed_response, current_turn) -> bool`.
**Data Shape:** pending items live on `run_state._pending_input`; admissions are wrapped as `InputItem`s carrying an `input_id`; acceptance is computed as set intersection with `tracker.accepted_input_item_ids`.

### Decisive source
```python
if session is not None and server_conversation_tracker is None:
    await save_result_to_session(session, [], admission_items, None, store=store, wrapper=wrapper)
if server_conversation_tracker is None:
    run_state.clear_pending_input()
return admission_items
```
Server path: retain only accepted admissions in generated/session lists; UNACCEPTED ones go BACK into `run_state._pending_input` via deep copy. If NO admission was accepted ("a model input filter may omit every staged occurrence"), return False — normal turn processing owns the response and the input remains available for a later request.

**Flow:** caller MUST run pending-input guardrails first. Client-managed session ⇒ save immediately, clear staging. Server-managed ⇒ keep staged; wrap into InputItems and extend model/new-item lists; after the model responds, `on_response_accepted` → commit: accepted IDs prune both lists, unaccepted re-stage; on success also append the model response, record `processed_response` as `_last_processed_response`, install `NextStepInterruption(response_accepted=True)` when applicable, sync conversation ids, and CLEAR the merged-marker because "the accepted model response is durable, but its processed items have not yet been merged — preserve that distinction across retries."

**Invariant:** Server-accepted-ness is the single commit criterion; local persistence before acceptance risks orphaned history the provider never saw. Unaccepted ≠ lost — it re-stages verbatim (deep-copied).

**Probe:** `tests/test_run_state_pending_input.py::test_failed_server_managed_request_keeps_pending_input_for_retry` (:570), `test_streamed_after_turn_cancel_keeps_pending_input_for_next_resume` (:320).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openai-agents-python", query: "admit pending input commit server tracker accepted ids", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the client/server split for any architecture where history may be owned by a remote store; adapt ID semantics to your transport; omit the guardrail pre-condition only if you have no input guardrails.

<!-- capsule-v2 -->
# Completion Bookkeeping Latches — what gets stamped, gated, and omitted when a human answer lands

**Source:** awaithumans Apache-2.0 `main@bc05b8e7`; Codebase Memory `mnt-hdd-utopia-inspo-awaithumans`. **Question:** In one completion transaction, which fields are latched to specific outcomes and which observability must redaction also gate?

## Connected graph-selected seam
**Path/Symbol:** `packages/python/awaithumans/server/services/task_service.py` — `complete_task` body tail (:400-481); label helper `audit_action_for` in `services/task_verifier.py` (:164-178).
**Signature:** `audit_action_for(status: TaskStatus, outcome: VerifierOutcome | None) -> str`; update dict assembled into one conditional UPDATE (`WHERE status NOT IN terminal`).
**Data Shape:** `update_values{status, response, updated_at, completed_by_email, completed_by_user_id, completed_via_channel[, completed_at][, verifier_result, verification_attempt]}` + `AuditEntry.extra_data{response_keys?, verifier_passed?, verification_attempt?, verifier_reason?}`.

### Decisive source
```python
    # Only stamp completed_at on actual completion. REJECTED is
    # non-terminal — leaving completed_at null lets the dashboard
    # render "in review" correctly across a rejection cycle.
    if target_status == TaskStatus.COMPLETED:
        update_values["completed_at"] = now
```
Redaction gates derived observability too (:448-459):
```python
    # Honour `redact_payload` here too — the audit trail is operator-
    # facing but ends up in logs, exports, and the dashboard. ...
    if response and not task.redact_payload:
        audit_extra["response_keys"] = list(response.keys())
    if verifier_outcome is not None:
        audit_extra["verifier_passed"] = verifier_outcome.result.passed
        audit_extra["verification_attempt"] = verifier_outcome.new_attempt
        if not task.redact_payload:
            # Reason can quote payload back at us; gate on redaction.
            audit_extra["verifier_reason"] = verifier_outcome.result.reason
```
Channel resolution prefers the authoritative kwarg (:461-464): `resolved_channel = channel if channel is not None else completed_via_channel`.
Label ladder (:164-178): outcome None ⇒ "completed"; COMPLETED ⇒ "verified"; VERIFICATION_EXHAUSTED ⇒ "verification_exhausted"; else "rejected" — "Distinct labels make the audit page readable without joining against verifier_result."

**Flow:** snapshot → commit → evaluate_submission (verifier may run seconds) → target_status chosen → ONE conditional UPDATE re-checking non-terminal (rowcount==0 ⇒ loser raises TaskAlreadyTerminalError after refresh) → audit row appended in the same unit of work → commit.
**Invariant:** `completed_at` is a COMPLETED-only latch (null through rejection cycles so UI renders "in review"); `redact_payload` gates BOTH the payload itself AND derived fields that could quote it (key names, verifier reason); embed callers' explicit `channel` kwarg overrides the body's self-reported channel so audits record the truth. Everything lands atomically — a crash mid-verifier leaves no half-written completion.

**Probe:** direct tests for this exact seam are INDIRECT — `test_verifier_polish.py::test_redact_payload_skips_verifier_entirely` (:77-110) and `test_response_redaction.py` cover the redact latch family; reject-cycle coverage rides test_verifier_integration (recorded caveat inside the capsule). Line-checked byte-exact at pin: :418-422, :448-459, :461-464, :164-178.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-awaithumans", query: "audit action for outcome verifier reason response keys redact extra data bookkeeping", limit: 5 });
```
Live at pin: rank-1 `audit_action_for` −35.95 (task_verifier.py :164-178); `_redact_response_if_requested` −24.29 (webhook_dispatch.py :253-287 — delivery-side twin already owned by webhook-retry-queue coverage); applyOptimisticRedaction −18.25.

## Verdict
Adopt outcome-keyed latches (completed_at on success only), redaction as a gate over DERIVED observability (not just raw payloads), and distinct human-readable audit labels per outcome. Adapt the label vocabulary to your statuses. Omit the channel-kwarg precedence only if your transports cannot misreport their own channel.

<!-- capsule-v2 -->
# Verifier Loop — how do LLM-judged human submissions retry without burning attempts on infra failures?

**Source:** awaithumans Apache-2.0 `main@bc05b8e7`; Codebase Memory `mnt-hdd-utopia-inspo-awaithumans`. **Question:** Where exactly do the session-release, redaction skip, attempt accounting, and NL-parse boundaries live in a verifier-augmented completion path?

## Snapshot-commit-verify-reupdate with provider-failure immunity
**Path/Symbol:** `packages/python/awaithumans/server/services/task_verifier.py:evaluate_submission` (:55–130) + `VerifierOutcome` (:35–52) + `previous_rejections_for/audit_action_for` (:133–168); call site `task_service.complete_task` (:376–441); providers under `server/verification/{prompt,runner,providers/*}`.
**Signature:** `evaluate_submission(task, *, response, raw_input) -> VerifierOutcome(result, new_attempt, target_status, parsed_response)`; deliberately takes NO AsyncSession.
**Data Shape:** outcomes: pass⇒COMPLETED; reject w/ attempts left⇒REJECTED (non-terminal, resubmitable); reject exhausted⇒VERIFICATION_EXHAUSTED (terminal). Provider/config failures propagate as ServiceError subclasses WITHOUT incrementing attempts.

### Decisive source
```python
# complete_task: release the DB connection BEFORE the 5–30s LLM round trip,
# passing a detached snapshot so verifier correctness never depends on
# expire_on_commit settings.
task_snapshot = _snapshot_task_for_verifier(task)
await session.commit()
verifier_outcome = await evaluate_submission(task_snapshot, response=response, raw_input=raw_input)
```
```python
new_attempt = task.verification_attempt + 1
if result.passed:                     target = TaskStatus.COMPLETED
elif new_attempt >= config.max_attempts: target = TaskStatus.VERIFICATION_EXHAUSTED
else:                                 target = TaskStatus.REJECTED
parsed = result.parsed_response if (result.passed and raw_input) else None
```

**Flow:** guard `verifier_config and not redact_payload` (redacted tasks are NEVER shipped to third-party LLMs — verification silently skipped, treated as unconfigured) → snapshot → commit/release → LLM verdict (+NL raw_input parsing when no structured form was submitted; parsed value REPLACES stored response) → guarded UPDATE back in caller → audit label derived from outcome (`completed`/`verified`/`rejected`/`verification_exhausted`). Prompt carries prior rejection reason so the human sees WHY on resubmit.
**Invariant:** only a real `passed=False` verdict counts toward max_attempts — missing API key/vendor outage/malformed config burn nothing because the LLM never rendered a verdict. Verifier reason is operator-controlled LLM output that may quote payload back: logged at DEBUG, excluded from audit extra_data under redact_payload.
**Probe:** `tests/tasks/test_verifier_integration.py` (:81–210 straight-complete / pass-stores-result / reject-resubmit-attempt-advance / exhausted-terminal / NL-parsed-response-replaces / **provider-failure-does-not-burn-an-attempt** :212).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-awaithumans", query: "evaluate_submission verifier outcome rejected", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt snapshot-across-LLM-boundary, connection-release-before-slow-call, provider-failure≠attempt, redaction-skips-third-party-shipping, and outcome-derived audit labels. Adapt prompt/provider plumbing. Omit vendor SDK specifics (providers/* are thin clients over constants-pinned defaults).

<!-- capsule-v2 -->
# Throttler replay patching — how does an immortal workflow adopt new behavior without corrupting in-flight histories?

**Source:** growchief AGPL-3.0 `main@abb1e37a6f5595d8d105aef5871a2eeb0c22a1dc`; Codebase Memory `growchief`. **Question:** when a per-bot workflow is designed to run forever via `continueAsNew`, how do you ship a new side effect without breaking deterministic replay of already-running histories?

## Connected graph-selected seam
**Path/Symbol:** `apps/orchestrator/src/workflows/workflow.throttle.ts` — `patched` imported from `@temporalio/workflow` (:9), applied at the notification call site :290–297.
**Signature:** `patched(patchId: string): boolean` (Temporal SDK primitive; here `patched('notifications-01-09-2025')`).
**Data Shape:** boolean gate keyed by an opaque, immutable patch ID; true only for executions started (or continued-as-new) after the patch was deployed; false inside replays of older histories.

### Decisive source
```ts
import {
  proxyActivities, setHandler, sleep, condition,
  getExternalWorkflowHandle, continueAsNew, startChild,
  patched,
} from '@temporalio/workflow';
...
if (patched('notifications-01-09-2025') && restriction) {
  await sendNotification({
    orgId: job.orgId, title: 'Restrictions',
    message: restriction.message, sendEmail: true,
  });
}
```

**Flow:** restriction arrives in a progress result → the version gate asks "does THIS execution's history know about notifications?" → old histories (pre-patch bots still running from before deploy) skip the branch and replay cleanly → new/continued runs take the branch and record the marker in history → every future replay of either shape stays deterministic.
**Invariant:** any new side effect added to an immortal (`continueAsNew`) workflow must be wrapped in `patched()` — otherwise workers replaying pre-deploy histories execute code those histories never recorded, nondeterministically. The date-style ID is a **name, not logic**: uniqueness is the only requirement. Complementary `deprecatePatch()` exists for later cleanup but has zero occurrences at this pin (grep `patched` = exactly 2 hits: import + single gate) — the patch is live, not yet deprecated.
**Probe:** no upstream test runner exists (spec/test count = 0). Deterministic source pin: read `workflow.throttle.ts:1–30` (import block proves `patched` is Temporal's own primitive, not app code) and :287–297 (single gated call site); grep `patched` across `*.ts` returns exactly 2 matches.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "growchief", query: "patched patch date flag helper", limit: 6, fields: ["signature", "lines"] });
// graph has NO node for `patched` — it is an SDK symbol, not repo code; the import line in workflow.throttle.ts:9 is the decisive anchor
```
Note: BM25 misses bare SDK identifiers; cite the import site when retrieving.

## Verdict
Adopt the discipline: history-gate every post-deploy behavior change inside long-lived workflows (works with any durable-replay engine — Temporal patched, or your own per-execution feature-version stamp carried across snapshots). Adapt the gate mechanism to your scheduler if it lacks patching (e.g. store a `schemaVersion` in workflow state at snapshot time). Omit nothing behavioral here — the gate IS the contract. Coverage caveat: workflow.throttle.ts `no_recorded_issue`/`metadata_match`; no behavioral runner upstream.

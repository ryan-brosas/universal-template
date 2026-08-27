<!-- capsule-v2 -->
# Optimistic Response Redaction — how do you close the privacy window between submit-ACK and server-side redaction?

**Source:** awaithumans Apache-2.0 `main@bc05b8e7`; Codebase Memory `mnt-hdd-utopia-inspo-awaithumans`. **Question:** The reviewer's Submit is acknowledged instantly but the webhook-driven redaction lands seconds later on a scheduler tick — what renders in between?

## Pure client overlay that pre-plays the server's eventual shape
**Path/Symbol:** `packages/dashboard/app/(dashboard)/task/optimistic-redact.ts:applyOptimisticRedaction` (:25–42); render branch `packages/dashboard/components/submitted-response.tsx:SubmittedResponse/DeliveredPlaceholder` (:42–98); server twin `packages/python/awaithumans/server/services/webhook_dispatch.py:_redact_response_if_requested` (:253–287). Direct test: `optimistic-redact.test.ts` (:68–125).
**Signature:** `applyOptimisticRedaction(task: Task, now: Date = new Date()): Task` (pure).
**Data Shape:** Spread + three targeted overwrites: `response: null`, `response_redacted_at: now.toISOString()` (synthesized), `status: "completed"`. All other fields preserved verbatim (metadata, assignee, audit keys).

### Decisive source
```ts
return {
    ...task,
    // Clear the response so any sibling component reading
    // `task.response` sees nothing to render.
    response: null,
    // Synthesize the timestamp client-side. The server-side value
    // will replace this on the next loadTask fetch.
    response_redacted_at: now.toISOString(),
    // Flip to terminal so canSubmitResponse becomes false and the
    // form unmounts (rather than rendering alongside the placeholder,
    // which would defeat the privacy guarantee).
    status: "completed",
};

// submitted-response.tsx — redacted path takes PRIORITY over content:
if (responseRedactedAt) return <DeliveredPlaceholder timestamp={responseRedactedAt} />;
```
Reload half (`app/(dashboard)/task/page.tsx`) — the overlay must survive F5 while the dispatcher lags (:116–127):
```ts
// Carry forward client-side optimistic redaction. The
// server's response_redacted_at is the source of truth
// when it arrives, but until the webhook dispatcher fires
// the callback (which can lag the submit by seconds) the
// server still has the typed response. Re-apply the
// overlay so the reviewer never sees the content come
// back between submit and the dispatcher's tick.
const displayTask =
    submittedWithRedaction.current && !taskData.response_redacted_at
        ? applyOptimisticRedaction(taskData)
        : taskData;
```
Submit half (:172–181) — latch the ref AND wipe local copies:
```ts
if (task.redact_response_after_submit) {
    submittedWithRedaction.current = true;
    setTask((prev) => (prev ? applyOptimisticRedaction(prev) : prev));
    // Clear the typed values from local state so no
    // sibling component holds a copy in memory. ...
    setFormData({});
}
```

**Flow:** submit succeeds on a `redact_response_after_submit=true` task → page applies the overlay in the same tick AND sets the sticky `submittedWithRedaction` ref → every subsequent `loadTask` re-applies the overlay UNTIL the server's own `response_redacted_at` lands (the condition checks both), so the submit-ACK→dispatcher-tick window survives refreshes and poll cycles → once server truth arrives the raw fetch wins and the overlay retires itself. Typed inputs leave the DOM (status flip unmounts the form via `canSubmitResponse`) and the "Response delivered" placeholder shows the synthesized time. Server side: after successful callback delivery `_record_outcome` calls the twin, which nulls the column and stamps `response_redacted_at=now`.
**Invariant:** the status flip is load-bearing — without it the form renders alongside the placeholder and the guarantee is void. The overlay is STICKY across reloads: a one-way ref (`submittedWithRedaction`, :84) re-applies it on every fetch until server truth lands, closing the reload-shaped hole a pure per-submit overlay leaves. Post-submit memory hygiene wipes form state (`setFormData({})`) so no sibling component holds typed values after unmount. The overlay must not drop sibling-read fields (spread, never destructure-rebuild). Server twin is idempotent by skipping non-null `response_redacted_at`, keeping the FIRST successful-delivery stamp and avoiding a redundant write. Placeholder renders the timestamp in viewer-local timezone via Intl formatting with a raw-string fallback instead of crashing.
**Probe:** `optimistic-redact.test.ts` (:69–72 response nulled; :74–81 injectable clock stamps exactly; :98–106 status flip pins form-unmount behavior; :108–125 unrelated fields preserved verbatim). Page half line-checked at pin: sticky ref declared `task/page.tsx:84`, re-apply condition :123–126, latch+wipe :172–181. Deterministic source probe (vitest runner blocked): `grep -n 'status: "completed"' 'packages/dashboard/app/(dashboard)/task/optimistic-redact.ts'` → :40.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-awaithumans", query: "applyOptimisticRedaction DeliveredPlaceholder redact_response_after_submit", limit: 8, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt pure-function overlays that pre-play the server's eventual row shape whenever an async backend pass follows an acknowledged user action; adopt the priority rule (redacted branch before content branch) and the idempotent non-null skip server twin. Adapt which fields your UI treats as terminal triggers. Omit millisecond-precision promises for the synthesized stamp — it is display-only until replaced.

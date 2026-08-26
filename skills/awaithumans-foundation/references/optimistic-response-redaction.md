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

**Flow:** submit succeeds on a `redact_response_after_submit=true` task → page applies the overlay in the same tick → typed inputs leave the DOM (status flip unmounts the form via `canSubmitResponse`) and the "Response delivered" placeholder shows the synthesized time → next `loadTask` fetch returns the server truth and replaces the synthesized stamp. Server side: after successful callback delivery `_record_outcome` calls the twin, which nulls the column and stamps `response_redacted_at=now`.
**Invariant:** the status flip is load-bearing — without it the form renders alongside the placeholder and the guarantee is void. The overlay must not drop sibling-read fields (spread, never destructure-rebuild). Server twin is idempotent by skipping non-null `response_redacted_at`, keeping the FIRST successful-delivery stamp and avoiding a redundant write. Placeholder renders the timestamp in viewer-local timezone via Intl formatting with a raw-string fallback instead of crashing.
**Probe:** `optimistic-redact.test.ts` (:69–72 response nulled; :74–81 injectable clock stamps exactly; :98–106 status flip pins form-unmount behavior; :108–125 unrelated fields preserved verbatim). Deterministic source probe (vitest runner blocked): `grep -n 'status: "completed"' 'packages/dashboard/app/(dashboard)/task/optimistic-redact.ts'` → :40.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-awaithumans", query: "applyOptimisticRedaction DeliveredPlaceholder redact_response_after_submit", limit: 8, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt pure-function overlays that pre-play the server's eventual row shape whenever an async backend pass follows an acknowledged user action; adopt the priority rule (redacted branch before content branch) and the idempotent non-null skip server twin. Adapt which fields your UI treats as terminal triggers. Omit millisecond-precision promises for the synthesized stamp — it is display-only until replaced.

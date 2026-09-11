<!-- capsule-v2 -->
# Pending prompt queue — steer vs queue delivery with abort-window durability

**Source:** Cline Apache-2.0 `main@4f836ae7d0ed29ece7ef4a2a478deb470fdd056e`; Codebase Memory `ext-cline`. **Question:** How should typed-ahead user prompts behave while a turn is running or being aborted — which jump the line, and what survives an Escape?

## Dedupe-or-insert with steer unshift; queue ops stay live during aborts, drain refuses
**Path/Symbol:** `sdk/packages/core/src/runtime/turn-queue/pending-prompt-service.ts:54-413` (`PendingPromptService` + `PendingPromptsController`).
**Signature:** `enqueue(state, {prompt, mode?, delivery:"queue"|"steer", userImages?, userFiles?}) → SessionPendingPrompt[]`; `consumeSteer`, `shiftNext`, `requeueFront`, `update`, `delete`, `discardQueue`.
**Data Shape:** Entry id `` `pending_${Date.now()}_${nanoid(5)}` ``; snapshots expose `attachmentCount = images+files` instead of raw arrays.

### Decisive source
```ts
const existingIndex = state.pendingPrompts.findIndex(
    (queued) => queued.prompt === prompt);        // EXACT-text dedupe
if (existingIndex >= 0) {
    ... if (delivery === "steer" || existing.delivery === "steer") {
        state.pendingPrompts.unshift({ ...next, delivery: "steer" });  // promotion
    } else { state.pendingPrompts.push(next); }
}
...
// The queue survives aborts and is visible while one settles, so
// queue operations must keep working during the abort window ...
```

**Flow:** enqueue dedupes by exact prompt text (re-queueing same text moves/merges the entry; either party steering promotes it to front with delivery "steer") → controller emits `pending_prompts` and schedules a microtask drain gated on `!aborting && !drainingPendingPrompts && agent.canStartRun()` → drain shifts ONE entry, marks `drainingPendingPrompts`, sends; error finish ⇒ stop draining but DON'T requeue (prompt is already in the conversation, error surfaced); thrown send ⇒ requeueFront; finally-chained microtask continues only when status ∉ {failed, cancelled}. `consumeSteer` pulls the FIRST steer-delivery entry wherever it sits. Abort gesture on a queue-initiated turn calls `discardQueue` — stopping means stop the REMAINDER too. Update reorders: new-steer⇒unshift, was-steer-now-queued⇒push, else splice in place; empty normalized prompts throw.
**Invariant:** The queue MUTATES during the abort window but never DRAINS during it — typed-after-Escape joins the queue instead of being silently dropped, yet nothing auto-fires until the abort settles. Steer is consumed before any queued turn at run boundaries.
**Probe:** `grep -cF 'queued.prompt === prompt' .../pending-prompt-service.ts` → 1; `grep -cF 'must keep working during the abort window' ...` → 1; `grep -cF 'this.service.requeueFront(session, next);' ...` → 1; upstream tests "deduplicates prompts and prioritizes steer delivery", "keeps prompts enqueued while the session is aborting", "requeues a drained prompt when send fails".

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-cline", query: "PendingPromptService enqueue consumeSteer", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt dedupe-by-exact-text + steer-promotion + abort-window mutation rules; adapt id scheme and event names; omit hub/daemon transport around the controller. Runner blocked honestly (no node_modules); battery greps executed green.

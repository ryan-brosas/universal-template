<!-- capsule-v2 -->
# Turn-finalize ordering — after a streamed agent turn ends, in what order do settlement, persistence, and broadcast run, and what does each failure mode cost?

**Source:** relaticle AGPL-3.0 `main@6e3bf8dfb7c5`; direct source+test read (Codebase Memory MCP not connected this session). **Question:** A queued streaming agent job must meter credits, persist three different row decorations, and notify the client — what is the safe ordering, and how do queue-wait drift, cancellation, and provider rate limits each get their own path?

## Ordered handle() ladder + fixed then() finalize chain
**Path/Symbol:** `packages/Chat/src/Jobs/ProcessChatMessage.php` (`handle` :102-285, `then` finalize :229-258, `retryDelaySeconds` :286, `isRateLimited` :302, `failed` :312, `persistMentions` :559, `persistUserDocument` :611, `materializeAssistantDocument` :637, `resolutionKey` :716; 720L).
**Signature:** `handle(CreditService $creditService)`; finalize chain inside `$response->then(...)`: `ConversationResolved` broadcast → `settleReservation(...)` → `persistMentions()` → `persistUserDocument()` → `materializeAssistantDocument($streamedResponse)` → `broadcastFollowUps($streamedResponse)`.
**Data Shape:** mention rows: `{id: ULID, message_id, type, record_id, label, source: 'mention'|'page_context'}` bulk-inserted onto the latest user message row. Cancel flag: `Cache::pull("chat:cancel:{conversationId}")` — pull makes it single-shot.

### Decisive source
```php
if ($cancelled) {
    $creditService->settleReservedMinimum(..., reason: 'cancelled');
    ...
}
...
$this->persistMentions();
$this->persistUserDocument();
$this->materializeAssistantDocument($streamedResponse);
$this->broadcastFollowUps($streamedResponse);
```
```php
// Rate-limit / overloaded errors are transient -> release with backoff.
// release() does not count against MaxExceptions(1); attempts() increments
// each retry. Bounded by this cap AND the job's retryUntil() (now+3min).
```

**Flow:** (1) queue-wait drift gate: `HostedWorkspaceAccess::isPaused` re-checked AFTER the queue wait — a workspace can pause between send and run; refund (not settle) + billing-specific failure event. (2) `bindAuth()` sets the web guard user so tools resolve the actor in the queue; `releaseAuth()` in `finally`. (3) pending proposals superseded BEFORE the turn, summaries injected via `withSupersededProposals` so the model knows its earlier proposals died. (4) pre-model setup failure → refund + generic failure broadcast. (5) provider concurrency gate (`ProviderRateGate::tryAcquire` miss) → `release(random_int(1,4))` jitter, not failure. (6) streaming loop: each event checked against the single-shot cancel flag; cancelled → settle reserved MINIMUM with reason 'cancelled'. (7) success → the fixed finalize chain above: meter first (settleReservation with full token usage), then persist the three row decorations (mentions + page_context rows; user document JSON whose failure degrades to the column DEFAULT — message still readable; assistant document built independently from collapsed text), then follow-ups. (8) 429/529/503 (typed or raw RequestException) → release with `min(2**attempts, 30)` base, Retry-After honored up to 60s, +0-3s jitter, bounded by MAX_RATE_LIMIT_RETRIES and retryUntil(now+3min). (9) `failed()` → settle reserved MINIMUM (never refund — tokens may have been spent), supersede proposals, best-effort failed-turn backfill, failure broadcast.
**Invariant:** Settlement happens exactly once per turn and always through the turn's resolution key (`resolve-<turnId>`), so a late duplicate settle is a silent no-op under the unique `(team_id, idempotency_key)` index. Failure paths settle the MINIMUM, never refund — the provider may have consumed tokens even on error. Row-decoration failures must never lose the message text itself (documents degrade to defaults). The finalize order is fixed: meter before persist, persist before follow-ups.
**Probe:** `tests/Feature/Chat/ProcessChatMessageTest.php` (auth binding, refund-on-pause, settle-minimum-on-fail), `ProcessChatMessageSettlementTest.php` (settle-minimum not refund on job failure), `ProcessChatMessageDocumentMaterializationTest.php`, `ProcessChatMessageFailureTest.php`.

## Get live surrounding code
**Retrieve:** (canonical graph form; executed this session as exact-symbol grep fallback — hit confirmed)
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "ProcessChatMessage handle settleReservation persistMentions persistUserDocument materializeAssistantDocument ProviderRateGate retryDelaySeconds", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the ordered ladder: queue-wait entitlement re-check → auth bind → proposal supersession → provider gate with jittered release → single-shot cancel → meter-then-persist finalize chain with independent degradation per decoration → transient-only release with Retry-After-honoring backoff → settle-minimum terminal failure. Adapt the Laravel queue release/failed hooks, broadcast events, and cache cancel flag to your queue/stream stack. Companions: `chat-credit-reservation-ledger.md` (the reservation being settled), `chat-failed-turn-backfill.md` (step 9's persistence), `follow-up-chip-suggestion.md` (the final step).

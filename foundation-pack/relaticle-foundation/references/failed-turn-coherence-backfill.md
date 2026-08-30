<!-- capsule-v2 -->
# Failed-turn coherence backfill — how does a dead streaming turn leave a transcript that still makes sense?

**Source:** relaticle AGPL-3.0 `main@2c2a2456`; Codebase Memory `relaticle`. **Question:** after a mid-stream crash, what gets written so reload shows the user message plus a visible failure note — without duplicating turns that actually succeeded?

## Last-two-rows discriminator before any backfill insert
**Path/Symbol:** `packages/Chat/src/Jobs/ProcessChatMessage.php:persistFailedTurn` (:385-453) called from `failed()` (:310-337); failure copy from `failureMessage` (:339-352).
**Signature:** `private function persistFailedTurn(?Throwable $exception): void`.
**Data Shape:** `agent_conversation_messages` rows (role, content, document JSON, meta.error flag); store persists [user row, assistant row] ONLY on full stream success, THEN post-stream `then()` callbacks run un-guarded.

### Decisive source
```php
$lastTwo = $table->clone()
    ->where('conversation_id', $this->conversationId)->latest()
    ->orderByDesc('id')->limit(2)->get(['role', 'content']);
$turnAlreadyComplete = $last !== null && $last->role === 'assistant'
    && $prev !== null && $prev->role === 'user' && $prev->content === $this->message;
if ($turnAlreadyComplete) {
    return;                        // stream succeeded; a later step failed — DO NOT backfill
}
$storePersistedUser = $last !== null && $last->role === 'user' && $last->content === $this->message;
if (! $storePersistedUser) { /* insert the user row */ }
/* then insert assistant failure-note row with meta {error: true} */
```
The comment block documents the residual ambiguity honestly: identical consecutive messages (or repeated failed+backfilled pairs) are indistinguishable and degrade to "message lost" for that edge — never duplicates, never false error notes.

**Flow:** job fails terminally → settle minimum credit → supersede proposals → inspect last TWO transcript rows: complete-turn pattern ⇒ do nothing; user-row-present ⇒ only append note; neither ⇒ insert user row then note. Note content varies by exception class (timeout copy with seconds; rate-limit reassurance; generic).
**Invariant:** backfill is idempotent against BOTH failure modes of the old single-row check — no duplicate user rows on post-stream-step failures, no false error notes on successful turns. Ordering survives retries because UUIDv7 ids sort the backfilled pair before later real turns.
**Probe:** `tests/Feature/Chat/ProcessChatMessageFailureTest.php` (:55 coherent dead turn incl. credit+supersede, :104 completed turn untouched when post-stream step throws, :138 backfill despite prior completed turn, :170 timeout copy, :198 id ordering after retry).
**Coverage caveat:** identical-message residual documented in-source and accepted; not test-covered.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "persistFailedTurn failureMessage turnAlreadyComplete", limit: 6, fields: ["signature", "lines"] });
```

## Verdict
Adopt: last-N-rows state discrimination before compensating writes for any pipeline whose persistence happens late (stream success) but whose failure handling runs early (job failed hook). Adapt row shapes and copy. Omit Laravel\Ai exception classes.

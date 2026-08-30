<!-- capsule-v2 -->
# Failed-turn backfill — last-two-rows disambiguation with a documented residual

**Source:** relaticle AGPL-3.0 `main@2c2a2456`; Codebase Memory `relaticle`. **Question:** When a streamed AI turn dies mid-flight, how do you reconstruct a coherent transcript without duplicating messages that actually succeeded?

## persistFailedTurn()
**Path/Symbol:** `packages/Chat/src/Jobs/ProcessChatMessage.php`: `persistFailedTurn()` (:385-453) + 30-line design docblock (:354-384); invoked from `failed()` (:310-337) which also settles minimum credits and supersedes proposals.
**Signature:** `persistFailedTurn(?Throwable $exception): void` — writes to `agent_conversation_messages` via the query builder (UUIDv7 ids).
**Data Shape:** Reads last TWO rows `{role, content}`; inserts missing user row + visible assistant failure note (`meta: {"error": true}`, document built from failure text).

### Decisive source
```php
// Inspecting only the single latest row can't tell that case apart from "the stream
// died before the store wrote anything": the latest row would be the assistant reply,
// not the user message, so the old guard concluded the user message was never
// persisted and inserted a duplicate plus a false error note on a turn that actually
// succeeded. Looking at the last TWO rows lets us tell a truly complete turn (user then
// assistant, matching this message) apart from a genuinely dead one.
$turnAlreadyComplete = $last?->role === 'assistant' && $prev?->role === 'user'
    && $prev->content === $this->message;
if ($turnAlreadyComplete) { return; }

$storePersistedUser = $last !== null && $last->role === 'user' && $last->content === $this->message;
if (! $storePersistedUser) { /* insert user row */ }
```
Documented residual (:374-383): identical consecutive messages make a failed second turn indistinguishable from the first's `[user, assistant-note]` pair — it degrades to "message lost" for that one edge case, never a duplicate or false error note, "accepted rather than solved with more machinery."

**Flow:** job fails terminally → settle reserved credit as minimum ('job_failed') → supersede still-pending proposals → backfill: skip if last two rows already form THIS message's complete turn → ensure the user row exists (ConversationStore only flushes on stream success) → append assistant failure note with timeout- or rate-limit-specific copy.
**Invariant:** Backfill must be idempotent under retry and must NEVER fabricate a duplicate user row when the post-stream `then()` callbacks failed after the store wrote both rows — hence two-row inspection, not one.
**Probe:** `tests/Feature/Chat/ProcessChatMessageFailureTest.php` (:55 coherent failed turn, :104 no duplicate on post-stream-step failure, :138 backfills after prior completed turn, :198 id ordering vs retried turns).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "persistFailedTurn failed persistMentions ConversationStore flush", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt last-N-row state reconstruction with an explicitly accepted residual over inventing write-ahead logs. Adapt row schema and failure copy. Omit vendor ConversationStore internals. Direct tests pin all four polarities including ordering.

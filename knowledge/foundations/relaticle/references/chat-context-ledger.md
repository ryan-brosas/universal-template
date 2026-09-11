<!-- capsule-v2 -->
# Context ledger — recency-capped record memory with an anchor-exempt last slot

**Source:** relaticle AGPL-3.0 `main@2c2a2456`; Codebase Memory `relaticle`. **Question:** How do you give a stateless agent durable memory of which records a conversation referenced, without the set growing unbounded or losing the one record that matters most?

## contextLedger() anchor reservation
**Path/Symbol:** `packages/Chat/src/Jobs/ProcessChatMessage.php`: `contextLedger()` (:498-555) + docblock (:485-494); persistence via `persistMentions()` (:557-599) writing `agent_conversation_message_mentions` rows with `source: 'mention'|'page_context'`.
**Signature:** `contextLedger(): list<{type, id, label}>` — cap `CONTEXT_LEDGER_CAP = 10`.
**Data Shape:** Source table joined to messages by conversation; dedup key `type:record_id`; anchor = OLDEST `page_context` row.

### Decisive source
```php
// One slot before the cap: stop unless this row IS the anchor, so the
// final slot stays reserved for it (appended below) rather than being
// taken by whatever is merely next in recency.
if (count($ledger) === self::CONTEXT_LEDGER_CAP - 1
    && $anchorKey !== null && $key !== $anchorKey && ! isset($seen[$anchorKey])
) { break; }
...
if ($anchor !== null && $anchorKey !== null && ! isset($seen[$anchorKey])) {
    $ledger[] = [...$anchor...];   // appended LAST if recency evicted it
}
```
Why the anchor exists (:487-491): "Unlike a typed @mention, a page-context record's name never enters the message text — so once it falls off this ledger the agent loses it entirely (no id, no name, nothing left to fall back on). The conversation's OLDEST page_context row is therefore exempt from the recency cap."

**Flow:** every turn's job re-derives the ledger from persisted mention/page-context rows → newest-first walk dedups by type:id → stops at cap−1 unless the remaining row IS the anchor → anchor appended last if not already seen → handed to the agent as ambient context alongside superseded-proposal summaries and resolved-action receipts.
**Invariant:** The cap is total INCLUDING the anchor (reservation, not addition); page-context rows must be persisted even though their names never appear in message text.
**Probe:** `tests/Feature/Chat/PageContextBindingTest.php` (:294 ledger lists referenced records with ids, :309 empty when nothing referenced, :317 label sanitization, :394 multi-turn collapse into one slot).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "contextLedger persistMentions page_context CONTEXT_LEDGER_CAP", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt derived-from-ledger context with recency cap + semantic anchor exemption for any agent that needs bounded entity memory across turns. Adapt the source taxonomy and cap size. Omit TipTap document materialization details. Direct tests pin ordering, dedup, and sanitization.

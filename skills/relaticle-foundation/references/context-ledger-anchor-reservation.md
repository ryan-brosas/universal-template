<!-- capsule-v2 -->
# Context ledger anchor reservation — how does bounded recency memory keep the conversation's oldest referenced record from falling off?

**Source:** relaticle AGPL-3.0 `main@2c2a2456`; Codebase Memory `relaticle`. **Question:** when handing the agent a capped list of previously-referenced records, which item must never be evicted?

## Cap-minus-one scan with oldest page_context anchor appended last
**Path/Symbol:** `packages/Chat/src/Jobs/ProcessChatMessage.php:contextLedger` (:498-555), constant `CONTEXT_LEDGER_CAP = 10` (:57); anchors sourced from `agent_conversation_message_mentions` rows where `source = 'page_context'` (persisted by `persistMentions` :557-599).
**Signature:** `private function contextLedger(): array<int, array{type: string, id: string, label: string}>`.
**Data Shape:** mention rows (type, record_id, label, source ∈ mention|page_context, created_at) joined to messages of the conversation, scanned newest-first, deduped by `type:record_id`.

### Decisive source
```php
// Distinct records referenced earlier in this conversation, most recent first.
// Unlike a typed @mention, a page-context record's name never enters the message
// text — so once it falls off this ledger the agent loses it entirely (no id, no
// name, nothing left to fall back on). The conversation's OLDEST page_context row
// is therefore exempt from the recency cap: it reserves the ledger's last slot ...
if (count($ledger) >= self::CONTEXT_LEDGER_CAP) {
    break;
}
// One slot before the cap: stop unless this row IS the anchor, so the
// final slot stays reserved for it (appended below) rather than being
// taken by whatever is merely next in recency.
if (count($ledger) === self::CONTEXT_LEDGER_CAP - 1 && $anchorKey !== null
    && $key !== $anchorKey && ! isset($seen[$anchorKey])) {
    break;
}
...
if ($anchor !== null && $anchorKey !== null && ! isset($seen[$anchorKey])) {
    $ledger[] = [...$anchor...];     // appended even if older than everything kept
}
```

**Flow:** query all mentions newest-first → dedupe by type:id → fill up to CAP but halt one slot early while the oldest page_context anchor is still unseen → append anchor explicitly → return ≤CAP entries. The result feeds `$agent->withContextLedger()` so the model can re-resolve "that company" without a fresh mention.
**Invariant:** total ledger size stays ≤ CAP regardless of how many distinct records were touched; the anchor occupies the reserved slot ONLY if not already present (no duplicates); typed mentions are allowed to age out because their names survive in message text — only context-free references need the guarantee.
**Probe:** deterministic source pins (no dedicated unit test at this pin): `grep -n 'CONTEXT_LEDGER_CAP' packages/Chat/src/Jobs/ProcessChatMessage.php` → :57/:523/:530; anchor filter `'source === \'page_context\''` → :507. Adjacent behavior tests: `PageContextBindingTest.php` (page-context binding into turns), `MentionsPersistenceTest.php`/`MentionsTest.php` (mention persistence feeding this table).
**Coverage caveat:** the anchor-reservation branch itself has no direct test — verified by whole-source read; treat as source-evidenced.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "contextLedger CONTEXT_LEDGER_CAP page_context persistMentions", limit: 6, fields: ["signature", "lines"] });
```

## Verdict
Adopt: anchor-reserved bounded recency for any rolling memory handed to an LLM — identify which items lose ALL grounding when evicted (not just recency value) and reserve their slot explicitly. Adapt cap size and anchor definition. Omit nothing else; the loop is small and complete.

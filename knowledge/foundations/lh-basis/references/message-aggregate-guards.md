<!-- capsule-v2 -->
# Message aggregate guards — How much field-level typing does an aggregate guard owe you, and when does a pending (unpersisted) entity become behavior-bearing?

**Source:** Linked Helper v2.130.5 ingest (proprietary — citations-only), pin `?@?`; Codebase Memory `lh-basis` @ 2026-08-23T00:11:49Z. **Question:** within one whitelist guard, which fields get type checks and which stay presence-only — and what changes for an entity that has not been sent yet?

## isIMessage: selective typing inside a 10-prop whitelist
**Path/Symbol:** `core/public-methods/models/messages/Message/guards.js` — `isIMessage` (8–27); `core/public-methods/models/messages/PendingMessage/guards.js` — `isIPendingMessage` (8–13).
**Signature:** `isIMessage(data): boolean`; `isIPendingMessage(data): boolean`.
**Data Shape:** message = DB item + 10 whitelisted props (`type`, `subject`, `text`, `attachmentsCount`, `externalIdentifiers`, `from`, `sendAt`, `chat`, `originalId`, `liAccountId`) with exactly five type-checked. PendingMessage = DB item + 6 props (`chatId`, `chat`, `text`, `createdAt`, `receiverPersonId`, `prevMessage`) + valid-DBId chatId + method surface.

### Decisive source
```js
function isIMessage(data) {
    return (isIDBItem(data) &&
        objectHasProperties(data, [
            'type', 'subject', 'text', 'attachmentsCount',
            'externalIdentifiers', 'from', 'sendAt', 'chat',
            'originalId', 'liAccountId',
        ]) &&
        typeof data.type === 'string' &&
        (typeof data.subject === 'string' || data.subject === null) &&   // the ONLY nullable-typed slot
        typeof data.text === 'string' &&
        typeof data.attachmentsCount === 'number' &&
        typeof data.liAccountId === 'number');
}
function isIPendingMessage(data) {
    return (isIDBItem(data) &&
        objectHasProperties(data, ['chatId', 'chat', 'text', 'createdAt', 'receiverPersonId', 'prevMessage']) &&
        isDBId(data.chatId) &&                       // value-checked, not just present
        objectHasMethods(data, ['delete', 'setText']));
}
```

**Flow:** dbItem -> whitelist presence -> primitive checks on scalar/value fields ONLY (`subject` explicitly accepts `null` alongside string; relation fields `from`/`sendAt`/`chat`/`originalId` and `externalIdentifiers` stay presence-only, their depth lives in sub-guards) -> pending variant adds a VALUE check on its foreign key (`chatId` must pass `isDBId`) plus a two-mutation behavior surface.
**Invariant:** typing depth follows field role: identity/account scalars are typed; relations are pinned by presence (their own guard families validate them elsewhere). A pending message is a live object, not a row projection: it carries mutators (`delete`, `setText`) exactly like Collections carry `add`/`remove` — if your "pending" port has no methods, it is a different type.
**Probe:** `node -e`: message fixture passes; flip `subject` to `undefined` → `false` but `null` → `true` (nullable-typed, not optional); `attachmentsCount:'3'` → `false`. Pending fixture passes; replace chatId with plain `{id:1}` object → `false`; non-callable `delete` → `false`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "lh-basis", qualified_name: "lh-basis.core.public-methods.models.messages.Message.guards.isIMessage" });
```

## Verdict
Adopt selective typing: type only the fields whose wrong values corrupt invariants (account id, counters, text); pin relations by presence and delegate to their families; model nullable-but-required with explicit `|| x === null`. Adapt prop lists. Omit LinkedIn message vocabulary. Coverage: no_recorded_issue ×2 @ gen 2026-08-23T00:11:49Z; probes executed against shipped dist modules (no test runner in ingest — standing block).

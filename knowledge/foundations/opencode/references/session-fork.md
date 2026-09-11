<!-- capsule-v2 -->
# Session fork — how do you copy a conversation up to a chosen message without breaking ID references?

**Source:** opencode (Slate-licensed monorepo) @ `dev@4643e65a`; Codebase Memory `opencode`. **Question:** How does forking a session copy the chronological message prefix into a new session while remapping every cross-reference?

## Fork as graph rewrite
**Path/Symbol:** `packages/opencode/src/session/session.ts` (`fork`, lines 693-734; `getForkedTitle`, :161-169).
**Signature:** `fork({sessionID, messageID?}): Effect<Info, NotFound>` — copies messages strictly BEFORE `messageID` (or all when omitted) into a fresh session.
**Data Shape:** New IDs from monotonic generators (`MessageID.ascending()`, `PartID.ascending()`); `idMap: Map<oldID,newID>` carries the translation. Title appends/increments `(fork #N)` by regex instead of stacking suffixes.

### Decisive source
```ts
// session.ts:704-732
const msgs = yield* messages({ sessionID: input.sessionID })
const idMap = new Map<string, MessageID>()
const target = input.messageID ? msgs.findIndex((msg) => msg.info.id === input.messageID) : msgs.length
for (const msg of msgs.slice(0, target < 0 ? msgs.length : target)) {
  const newID = MessageID.ascending()
  idMap.set(msg.info.id, newID)
  const parentID = msg.info.role === "assistant" && msg.info.parentID ? idMap.get(msg.info.parentID) : undefined
  const cloned = yield* updateMessage({ ...msg.info, sessionID: session.id, id: newID, ...(parentID && { parentID }) })
  for (const part of msg.parts) {
    const p: SessionV1.Part = { ...part, id: PartID.ascending(), messageID: cloned.id, sessionID: session.id }
    if (p.type === "compaction" && p.tail_start_id) p.tail_start_id = idMap.get(p.tail_start_id)
    yield* updatePart(p)
  }
}
```

**Flow:** get original (404 propagates) → derive forked title → createNext with `structuredClone(original.metadata)` (copied by value — pinned by test `not.toBe`) → replay messages through updateMessage/updatePart so the SAME event pipeline that persists live traffic persists the clone → return new Info.
**Invariant:** The prefix is CHRONOLOGICAL (from `messages()`), not storage order — pinned by `"forks the chronological prefix across mixed message ID ordering"` where IDs deliberately wrap lexically (`msg_z9-before`, `msg_a0-after`). An unknown `messageID` (findIndex −1) forks NOTHING rather than everything — fail-closed. Assistant parentID and compaction `tail_start_id` are the ONLY reference fields remapped; anything referencing messages outside the prefix would dangle, so porters must enumerate reference fields for their schema. Fork metadata is a deep copy, never shared.
**Probe:** `packages/opencode/test/session/session.test.ts:231-266` (metadata copy + both wrap-direction prefixes); persistence side: `packages/opencode/test/session/messages-pagination.test.ts:803`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "Session.fork createNext session.ts", limit: 10 });
```

## Verdict
Adopt event-replay cloning + old→new ID map + chronological-prefix/unknown-cutoff-fails-closed semantics. Adapt which part types carry cross-message references to your own schema. Omit the title regex if your UX doesn't number forks.

<!-- capsule-v2 -->
# Contributor attribution — how do you know WHICH users changed a page since the last save/history?

**Source:** docmost AGPL-3.0 `main@549cf7c0053bb4f4c3c4e08d588b1f0c69297daf`; Codebase Memory `ext-docmost`. **Question:** How are per-document editor identities accumulated in memory and drained exactly once into page contributors and history?

## onChange set → consumeContributors drain → Redis SADD/SP0P handoff
**Path/Symbol:** `apps/server/src/collaboration/extensions/persistence.extension.ts`:`onChange` / `consumeContributors` / `afterUnloadDocument` (lines 220–244); `apps/server/src/collaboration/services/collab-history.service.ts`:`addContributors` / `popContributors` (lines 15–25).
**Signature:** `onChange(data: onChangePayload): Promise<void>`; `consumeContributors(documentName: string): string[]`; `popContributors(pageId: string): Promise<string[]>`.
**Data Shape:** In-memory `Map<documentName, Set<userId>>` per collab process; cross-process continuation via Redis set `history:contributors:<pageId>`.

### Decisive source
```ts
async onChange(data: onChangePayload) {
  const userId = data.context?.user?.id;
  if (!userId) return;                       // unauthenticated/direct connections contribute nothing
  this.contributors.get(documentName)?.add(userId) ?? this.contributors.set(documentName, new Set([userId]));
}
private consumeContributors(documentName: string): string[] {
  const s = this.contributors.get(documentName);
  if (!s) return [];
  const userIds = [...s];
  this.contributors.delete(documentName);    // drain-on-read: each store flush claims its editors once
  return userIds;
}
```
History processor hands off across processes with Redis: `SADD history:contributors:<pageId> ...ids`, then `SCARD` + `SPOP count` to atomically pop the whole set.

**Flow:** every doc change tags the authenticated user → store flush drains the set, unions it with existing `contributorIds` + creator, writes the union → same ids re-added to Redis for the async history job → history job pops them when it actually snapshots.
**Invariant:** attribution requires a resolved auth context — anonymous changes are never attributed. Drain-on-read guarantees a user appears on exactly one save boundary; the Redis round-trip exists because the BullMQ worker may run on ANOTHER machine than the collab process that saw the edits. History failure path re-adds popped ids (`collabHistory.addContributors`) so attribution survives a failed snapshot attempt.
**Probe:** `grep -cF 'consumeContributors(documentName)' apps/server/src/collaboration/extensions/persistence.extension.ts` (=1) and `grep -cF 'spop(key, count)' apps/server/src/collaboration/services/collab-history.service.ts` (=1).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-docmost", query: "contributors onChange consumeContributors spop sadd", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt change-hook attribution + drain-on-read + cross-process Redis set handoff; adapt storage of the pending set; omit Nest injection. No upstream direct test; pinned by source read + probes.

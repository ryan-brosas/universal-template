<!-- capsule-v2 -->
# Session lineage reconstruction — how do you scope memory to the ACTIVE branch of a parent-linked session JSONL without trusting append order?

**Source:** pi-fabric MIT `feat/veda-runner@4874ac3abefab27ee0064a3c8571ee017ceb3115`; Codebase Memory `pi-fabric`. **Question:** how does memory indexing address only entries on the current conversation branch, with a fingerprint that invalidates on navigation?

## Parent-walk from the leaf, cycle-reported not thrown
**Path/Symbol:** `src/memory/lineage.ts:reconstructSessionLineage` (:68-114), `readPersistedNodes` (:28-52), `fingerprint` (:25-26).
**Signature:** `reconstructSessionLineage(sessionFile: string, branches: "active"|"all", liveBranch?: {entries: readonly unknown[]; leafId: string | null}): SessionLineage` where `SessionLineage = {branches; leafId; entryOrdinals: ReadonlySet<number> | null; fingerprint: string; coverageReasons: string[]}`.
**Data Shape:** persisted node = `{id, parentId: string | null, ordinal}` parsed per JSONL line (`type === "session"` header lines skipped; unparseable lines skipped but still advance the ordinal counter so ordinals stay dense positions); fingerprint = sha256 over `JSON.stringify({branches, leafId, ids})`.

### Decisive source
```ts
// "Reconstruct Pi 0.80.6's persisted leaf semantics without treating append
// order as a transcript: the final persisted entry is the leaf, duplicate IDs
// resolve to their LAST record in the ID map, and parent links are walked to
// a root. Cycles are stopped defensively and reported as incomplete coverage."
const leafId = liveBranch ? liveBranch.leafId : (nodes[nodes.length - 1]?.id ?? null);
let current = leafId ? byId.get(leafId) : undefined;
while (current) {
  if (seen.has(current.id)) { reasons.add("invalid_parent_graph"); break; }
  seen.add(current.id);
  path.push(current);
  current = current.parentId ? byId.get(current.parentId) : undefined;
}
path.reverse();
```
When a live SessionManager is present its branch entry ids are used directly instead of the walk.

**Flow:** `"all"` short-circuits to `{leafId: null, entryOrdinals: null}` (everything indexable, empty fingerprint inputs) → `"active"` reads the file, maps ids (last record wins for duplicates), and either adopts the live branch's ids or walks parent links from the leaf → emits the active-path ordinal set plus a fingerprint binding branch mode + leaf + id list, so any navigation/restart changes the key and stale caches miss.
**Invariant:** append order is NEVER treated as transcript order — membership comes from parent links (or the live manager), while ordinals remain pure line positions for addressing. A corrupt parent graph degrades coverage (`invalid_parent_graph`) rather than crashing or silently truncating.
**Probe:** `tests/memory-lineage-privacy.test.ts:78` ("defaults to the latest persisted parent-linked branch and exposes siblings only in all mode"), `:114` ("uses the current live SessionManager branch getter after navigation without an append"), `:201` ("refuses off-lineage addresses by default … binds active pointers to lineage").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "reconstructSessionLineage leaf parent walk fingerprint coverageReasons lineage", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt leaf-anchored parent-walk reconstruction, last-record-wins dedupe, ordinal-as-position addressing, and fingerprint-bound caches; adapt the node schema to your session format; omit pi-specific entry types.

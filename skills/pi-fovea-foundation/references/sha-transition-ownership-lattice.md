<!-- capsule-v2 -->
# Sha-transition ownership lattice — how does a chain of edits prove who owns the current content?

**Source:** pi-fovea MIT `main@5bd4e6f`; Codebase Memory `mnt-hdd-utopia-inspo-pi-fovea`. **Question:** Given only before/after content hashes of a drift, how do you decide the change was mine, theirs, both, or nobody's — without trusting file mtimes or locks?

## Reachability over (beforeSha → afterSha) edges
**Path/Symbol:** `src/core/provenance.ts:attributeChanges/kindForOwners/ownersForTransition` (:191-243).
**Signature:** `attributeChanges(root, sessionId, since, changes: {file, beforeSha?, afterSha?}[]): Promise<SyncProvenance>` where `SyncProvenance = {kind: "current-session"|"other-session"|"mixed"|"unattributed", files: Record<string, ProvenanceKind>}`.
**Data Shape:** states lattice `Map<shaKey, Set<owner>>`; `shaKey = sha ?? "\0deleted"` so deletions are first-class states; per-file records pre-sorted `at` asc, then owner, then commitOrder (missing commitOrder sorts LAST via MAX_SAFE_INTEGER), then toolCallId.

### Decisive source
```ts
const key = (sha: string | undefined): string => sha ?? "\0deleted";
states.set(key(beforeSha), new Set());
for (const record of records) {
  const owners = states.get(key(record.beforeSha));
  if (!owners) continue;                       // unreachable edge: skipped
  const nextKey = key(record.afterSha);
  const next = states.get(nextKey) ?? new Set<string>();
  for (const owner of owners) next.add(owner); // ownership FLOWS THROUGH
  next.add(record.owner);
  states.set(nextKey, next);
}
return states.get(key(afterSha)) ?? new Set();  // who can reach the final sha?
```

**Flow:** journal records for one file become directed sha→sha edges annotated with their session-owner → reachability from `beforeSha` accumulates owner sets at every reachable state → the owners of `afterSha` classify the drift: empty set = "unattributed" (external editor), one owner = me vs them, multiple = "mixed" → top-level kind aggregates the per-file kinds.
**Invariant:** A chain A:one→two then B:two→three makes THREE jointly owned (mixed) even though each write was single-session — co-editing is visible by construct; an edge whose before-sha is unreachable is ignored rather than guessed; identical before/after transitions are dropped at record time, never classified. Ordering matters ONLY within one owner's same-timestamp writes (commitOrder tiebreak) — cross-session interleaving resolves through shared shas, not timestamps.
**Probe:** `tests/provenance.test.ts` — "reports a transition chain owned by multiple sessions as mixed" (:105-116); "uses receipt commit order when timestamps cannot order one session's transitions" (:86-103); "leaves uninstrumented writes unattributed" (:118-129).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pi-fovea", query: "ownersForTransition attributeChanges SyncProvenance", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt reachability-over-hashes as the attribution primitive anywhere concurrent actors mutate shared state (files, rows, keys). Adapt the kind vocabulary to your UX (steer-now vs review-later). Omit pi-specific owner hashing.

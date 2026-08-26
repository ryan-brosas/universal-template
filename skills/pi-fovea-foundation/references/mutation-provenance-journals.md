<!-- capsule-v2 -->
# Mutation provenance journals — how is a file change attributed to the session that made it?

**Source:** pi-fovea MIT `main@5bd4e6f`; Codebase Memory `mnt-hdd-utopia-inspo-pi-fovea`. **Question:** Multiple agent sessions (and plain bash/external editors) mutate one repo — how can turn-sync tell which session caused a drift without any central authority?

## Per-session tempdir journals + per-target write queues
**Path/Symbol:** `src/core/provenance.ts:provenancePathFor/captureMutation/persistRecords/readRecords` (:48-189).
**Signature:** `captureMutation(root, path): Promise<MutationCapture|undefined>`; `recordMutationTransitions(root, transitions[], sessionId, toolCallId): Promise<number>`; `readRecords(root, since): Promise<MutationRecord[]>`.
**Data Shape:** `MutationJournal = {version:1, root(resolved), owner(sha1(sessionId)[:16]), records[]}`; record `{file, beforeSha?, afterSha?, owner, toolCallId, commitOrder?, at}`. Journal file = `${tmpdir()}/pi-fovea-provenance-${sha1(root)[:16]}-${owner}.json`. Caps: TTL 7d (`JOURNAL_TTL_MS`), 256 records/file (`JOURNAL_MAX_RECORDS`).

### Decisive source
```ts
const prefixFor = (root: string): string => `pi-fovea-provenance-${rootKey(root)}-`;
export const provenancePathFor = (root: string, sessionId: string): string =>
  join(tmpdir(), `${prefixFor(root)}${ownerFor(sessionId)}.json`);
// persistRecords: torn/missing journal recovers as fresh per-session file
if (existing.version === JOURNAL_VERSION && existing.root === journal.root && existing.owner === journal.owner) {
  records = existing.records.filter((item) => item.at >= cutoff);
}
// atomic publish: temp file named with pid+uuid then rename
await writeFile(temporary, JSON.stringify(journal));
await rename(temporary, target);
```

**Flow:** edit tool pre-captures `captureMutation` (hash BEFORE write) → after write `finishMutation` hashes again → `recordMutationTransitions` drops no-op transitions (beforeSha===afterSha) and appends the rest through a **per-journal-file promise queue** (`writeQueues` Map keyed by target path; each append chains on the previous via `.catch(()=>{}).then(...)`, self-cleans its map slot only if still head) → readers `readdir(tmpdir())` for the root's prefix, first awaiting all in-flight queued writes whose filename starts with that prefix (**read-your-writes drain**, :159-161) → version/root mismatched or torn files are skipped silently, fully-expired journals are unlinked inline.
**Invariant:** attribution survives process restarts (journals are on disk) but never crosses machines; a malformed/concurrently-replaced journal degrades to "unattributed", never an error; writes to one journal serialize but different sessions' journals don't block each other.
**Probe:** `tests/provenance.test.ts` — "attributes an exact content transition to the current or another session" (:43-56, same record answers current-session for A and other-session for B); "persists and attributes a multi-file receipt batch" (:69-84); "leaves uninstrumented writes unattributed" (:118-129).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pi-fovea", query: "attributeChanges ownersForTransition", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the pattern: content-hash transition receipts written per actor to crash-safe tempdir journals, read back by prefix scan. Adapt the tmpdir location/TTLs to your retention needs. Omit pi session-ID plumbing (any stable actor id works as owner key).

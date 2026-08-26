<!-- capsule-v2 -->
# Checkpoint store — persist and resume a deep-run checkpoint as YAML under a per-path lock

**Source:** Veda (`veda-ts`, MIT, `master@f050518c99fa54a5a0af4a04918aaf01d1ed94e1`); Codebase Memory `veda`. **Question:** How does a long-running deep pipeline persist its progress so it can resume after an interruption (e.g. API rate limit), and how does it validate and clear that state?

## Locked YAML checkpoint persistence
**Path/Symbol:** `src/checkpoint/store.ts:CheckpointStore` (23–139), using `withLock` from `src/util/lock` and path helpers `getCheckpointPath`/`getSessionDir`/`isValidSessionId` from `src/util/paths`.
**Signature:** `class CheckpointStore { constructor({ sessionId, baseDir? }); save(checkpoint); load() → DeepThinkCheckpoint|null; exists(); clear(); getSummary() }`.
**Data Shape:** `DeepThinkCheckpoint = { checkpoint_version: 1, runIdentityHash, trace, status: 'partial'|..., completedStage, failedStage?, error?, timestamp, successfulCandidateIds[], judgeSeed?, usageAtCheckpoint, ... }`. Stored as YAML at `<baseDir>/sessions/<sessionId>/checkpoint.yaml` (human-readable, trace-compatible).

### Decisive source
```ts
async save(checkpoint) {
  await withLock(this.checkpointPath, async () => {
    await mkdir(this.sessionDir, { recursive: true });
    const withTs = { ...checkpoint, timestamp: new Date().toISOString() };
    const yaml = yamlStringify(withTs, { lineWidth: 120, defaultKeyType: 'PLAIN', blockQuote: 'literal', collectionStyle: 'block' });
    await Bun.write(this.checkpointPath, yaml);
  });
}
async load() {
  return await withLock(this.checkpointPath, async () => {
    try {
      const file = Bun.file(this.checkpointPath);
      if (!await file.exists()) return null;
      const parsed = yamlParse(await file.text());
      if (parsed?.checkpoint_version !== 1) { console.warn(`Unknown checkpoint version: ${parsed?.checkpoint_version}`); return null; }
      return parsed as DeepThinkCheckpoint;
    } catch { return null; } // parse errors → treat as no checkpoint
  });
}
```

**Flow:** `save` stamps a fresh ISO timestamp, serializes the checkpoint to YAML, and writes it under a per-path lock (mirroring the ConversationStore locking pattern); `load` reads and validates `checkpoint_version === 1`, returning null on missing file, wrong version, or parse error; `clear` deletes the file under the lock; `getSummary` loads and returns `{ completedStage, failedStage, candidateCount, timestamp }` without exposing the full body.

**Invariant:** every write/read/delete is serialized under `withLock(checkpointPath)` so concurrent runs on the same session cannot corrupt the file; an unknown or unparseable checkpoint is treated as absent (never crashes the resume path); `save` always overwrites with a fresh timestamp; `clear` is called only on successful completion.

**Probe:** `tests/checkpoint/store.test.ts` — `exists` false when absent; `save`+`load` roundtrip preserves `checkpoint_version`, `runIdentityHash`, `status`, `completedStage`, `failedStage`, `successfulCandidateIds`, `trace.prompt`; `clear` removes it; `getSummary` returns summary without full load; `save` updates timestamp; `load` returns null for `checkpoint_version: 99`. Coverage caveat: `tests/` is excluded from the index by design (`fast-pattern`), so this probe is source-grounded from the on-disk test file, not graph-covered.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pi-ecosystem-veda", query: "CheckpointStore save load withLock checkpoint_version", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the locked, versioned YAML checkpoint store with save/load/clear/getSummary and the validate-or-treat-as-absent load contract. Adapt the file I/O (Bun → Node/Deno), the YAML options, and the checkpoint schema to the host. Omit the specific deep-run checkpoint fields (trace/judge mapping) unless a target needs them.

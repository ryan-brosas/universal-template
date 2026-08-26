<!-- capsule-v2 -->
# Temp run root retention — how do you garbage-collect crashed workers' temp dirs without ever deleting a live one?

**Source:** pi-fabric (MIT), `feat/veda-runner@4874ac3a`; Codebase Memory `pi-fabric`. **Question:** How can multiple processes share a temp-run directory namespace and safely reclaim roots left by dead or closed owners?

## Temp run root retention
**Path/Symbol:** `src/storage/retention.ts:sweepTempRunRoots/pruneClosedRunRoot/markRunRootActive/markRunRootClosed` (:124–178, :83–111, :53–74); archives `pruneActorRunArchives` :180–206.
**Signature:** `sweepTempRunRoots({tempRoot, currentRoot?, orphanedTempRunRetentionMs, oneShotRunRetentionMs, now?}): {removedRoots, removedRuns}`; owner file `.fabric-owner.json` `{pid, startedAt, heartbeatAt, orphanedAt?, closedAt?}`.
**Data Shape:** run roots named `pi-fabric-runs-*` under os.tmpdir(); each run subdir carries `status.json` `{status?, actorId?, finishedAt?, updatedAt?}`; TERMINAL_STATUSES = {"completed","failed","stopped","timed_out"}.

### Decisive source
```ts
const processAlive = (pid: number): boolean => {
  if (!Number.isInteger(pid) || pid <= 0) return false;
  try {
    process.kill(pid, 0);
    return true;
  } catch (error) {
    return !(error instanceof Error && "code" in error && error.code === "ESRCH");
  }
};
...
if (typeof owner.orphanedAt !== "number") {
      writeOwner(root, { ...owner, orphanedAt: now });   // FIRST sighting only STAMPS, never deletes
      continue;
}
```

**Flow:** sweep every `pi-fabric-runs-*` dir except currentRoot → no owner file + empty + old ⇒ remove; owner alive ⇒ skip; dead-PID first sight ⇒ stamp orphanedAt (grace window starts) → past orphanedTempRunRetentionMs ⇒ rm -rf; closedAt present ⇒ prune terminal RUNS inside by age (`finishedAt ?? updatedAt ?? dir-mtime` fallback), actor-owned runs on the SHORTER orphaned clock vs one-shot runs (`record.actorId ? orphaned : oneShot`) → empty root removed last.
**Invariant:** A live PID is NEVER collected regardless of age (kill(pid,0) probe treats EPERM as alive — only ESRCH means dead); the two-phase orphan stamp means a root survives at least one full grace window after its owner dies even in a single-sweep world; latestRunId is exempt from archive pruning; all reads are try/catch-tolerant so concurrent removal never crashes the sweeper.
**Probe:** `tests/retention.test.ts` ("expires terminal one-shot runs from gracefully retained roots after 24 hours" — expired+actorTemp removed, fresh kept); grep -c 'removes dead temporary run roots after six hours' tests/retention.test.ts → 1.
**Anchor:** repo root.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "sweepTempRunRoots pruneActorRunArchives markRunRootActive retention", limit: 10 });
// sweepTempRunRoots Function src/storage/retention.ts 124-178
```

## Verdict
Adopt the owner-file + two-phase orphan grace pattern for any multi-process temp-dir GC; adapt retention constants and status vocabulary; omit PID liveness probing on hosts where PIDs recycle faster than your grace window.

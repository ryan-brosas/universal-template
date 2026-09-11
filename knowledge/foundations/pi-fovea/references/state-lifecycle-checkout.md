<!-- capsule-v2 -->
# State lifecycle — how does a repo graph stay fresh across turns without re-probing the world every time?

**Source:** pi-fovea MIT `DETACHED@217a103`; Codebase Memory `pi-fovea`. **Question:** Resident state must serve instant reads, refresh against a drift oracle, survive checkouts quietly, and degrade gracefully when git vanishes — what is the generation lifecycle?

## Probe-gated refresh + checkout flag + plain-root walk/sweep gaps
**Path/Symbol:** `src/core/ops.ts:ensureState/refreshState/buildState/assembleState/factPass/graphVersion` (:77-328); git oracles `src/core/git.ts:gitProbe/gitReflogAction/gitPrefix` (:50-151).
**Signature:** `ensureState(root, {hints, force}): Promise<RepoState>` (inflight-deduped); `refreshState(state, hints, force): Promise<RepoState>`; `factPass(job)` serializes ALL fact passes through one never-rejecting chain.
**Data Shape:** `RepoState = {root, version (sha1[:12] of sorted file:sha1), graph, csr, adjacency (pre-sorted), facts (immutable Record snapshot), extraction report, store (live), files, gitKind, head, dirty, history, checkout?, probedAt/walkedAt/sweptAt}`. Env gaps: WALK_GAP_MS 4s / SWEEP_GAP_MS 20s.

### Decisive source
```ts
// A checkout re-materializes the worktree from another ref; flag the rebuilt
// generation so sync re-baselines quietly. Only a HEAD move whose latest
// reflog action is "checkout:…" qualifies — pulls/rebases merge foreign work
// and keep the loud drift path, and reflog-less repos stay conservative.
let checkout = false;
if (headMoved) checkout = (await gitReflogAction(root))?.startsWith("checkout:") ?? false;
// Porcelain-clean with unmoved HEAD hides reverts: a previously dirty file
// vanishes from the probe while its captured facts stay dirty. Resurrect it
// once so the snapshot follows the worktree — stat is the arbiter.
for (const p of state.dirty) {
  if (nowDirty.has(p)) continue;
  const onDisk = await stat(join(root, p)).then((s) => s.isFile(), () => false);
  if (onDisk) changed.push(p); else deleted.push(p);
}
```

**Flow:** ensureState → inflight dedupe → warm? refresh : cold build (ast-grep availability gate throws install guidance; listFiles via `git ls-files -co --exclude-standard`, umbrella dirs stop at nested `.git` markers). refreshState → union tool hints into candidates → git probe (`status --porcelain=v1 -z --no-renames`); parse surprise or collapsed untracked dirs trigger a relist; HEAD-moved+clean sweeps everything once; D-codes delete only KNOWN files; porcelain-clean resurrect path via stat → refreshFacts through the serialized fact chain → noDelta short-circuit keeps the same generation → else assemble a fresh immutable snapshot and swap it in. `.git` vanished mid-life degrades to plain mode (walk/sweep gaps).
**Invariant:** The probe is the correctness ORACLE (~40 ms is paid over turn-shortcuts); facts track the last seen worktree while porcelain diffs vs HEAD — hence the dirty-resurrection rule. `checkout` lives exactly ONE generation so the quiet path can't hide authored drift. All fact passes serialize because the failure ledger is process-global (nested passes would misblame files).
**Probe:** `tests/sync.test.ts` — "re-baselines quietly on a branch switch… measures drift against the new ref" (checkout flag asserted then gone next generation); "follows the worktree when a dirty file returns to porcelain-clean" (version returns to pristine after revert); `tests/report.test.ts` umbrella/nested-.git fixtures.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pi-fovea", query: "refreshState checkout gitProbe factPass", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt inflight-deduped resident generations, probe-as-oracle with hint unions, reflog-qualified checkout quieting (one generation), stat-arbitrated resurrection, serialized fact passes, and plain-root gap-based sweeping. Adapt gap timers and probe cadence to your host loop. Omit nothing — each branch encodes a recorded failure mode.

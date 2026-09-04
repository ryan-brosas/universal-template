<!-- capsule-v2 -->
# Version-pinned hook-mirror harness — how do you drive a host's unexported internal API deterministically, and measure whether a hook reads the previous summary without hardcoding the answer?

**Source:** pi-fabric MIT `feat/veda-runner@4874ac3abefab27ee0064a3c8571ee017ceb3115`; Codebase Memory `pi-fabric`. **Question:** when your extension hooks a host whose public export map omits the function you must call, how do you certify against it honestly — and force compaction eligibility in tests without giant fixtures?

## Certified-version pin + resolved-internal-module probe + Proxy-counted previousSummary reads
**Path/Symbol:** `scripts/certification/pi-compaction.mjs` whole (119L): version pin (:15-27), `PI_COMPACTION_API` (:29-36), `SMALL_COMPACTION_SETTINGS`/`SMALL_CONTEXT_WINDOW` (:38-44), `getPiContextTokens` (:46-47), `prepareEligibleCompaction` (:49-71), fake-host hook capture (:73-80), `invokeRegisteredFabricCompactor` (:82-108), expected-context algebra (:110-119).
**Signature:** `prepareEligibleCompaction(manager, settings?, contextWindow?): {branchEntries, builtEntries, publicBuiltEntries, contextTokens, contextWindow, eligible, preparation}`; `invokeRegisteredFabricCompactor({preparation, branchEntries, customInstructions?}): {event, result, instrumentation:{previousSummaryReads, priorSummaryFedAsInput}}`.

### Decisive source
```ts
const CERTIFIED_PI_VERSION = "0.83.0";
if (piPackage.version !== CERTIFIED_PI_VERSION) throw new Error(…);
const internalCompaction = await import(pathToFileURL(path.join(
  piPackageRoot, "dist", "core", "compaction", "compaction.js")).href);
if (typeof internalCompaction.prepareCompaction !== "function"
  || typeof internalCompaction.estimateContextTokens !== "function") throw new Error(…);
// Proxy instrumentation — the verdict is MEASURED from access counts:
let previousSummaryReads = 0;
const instrumentedPreparation = new Proxy(preparation, { get(target, property, receiver) {
  if (property === "previousSummary") previousSummaryReads += 1;
  return Reflect.get(target, property, receiver);
}});
```

**Flow:** module load hard-fails unless the installed host is EXACTLY the certified version and its internal dist module still exposes the two needed functions — certification can't silently run against drifted internals. `PI_COMPACTION_API` records which functions are publicly exported vs reached via the resolved internal module, so the report never overclaims ("prepareCompactionPubliclyExported: false" is stated outright in docs/certification.md). Tiny settings (`contextWindow=64, reserveTokens=63, keepRecentTokens=1`) make Pi's own `shouldCompact` return true on toy sessions — eligibility is forced by configuration, not by huge fixtures. The fabric hook is captured onto a FAKE pi host (`on("session_before_compact")`) and invoked with a host-shaped event; wrapping the preparation in the read-counting Proxy derives `priorSummaryFedAsInput` from actual property accesses. Expected post-compaction context is pure algebra: `[compactionEntry, ...branch.slice(indexOf(firstKeptEntryId))]`, compared by id+type pairwise.
**Invariant:** the poison protocol (docs :27) pairs with the Proxy: every persisted summary carries a cycle-unique `PRIOR_SUMMARY_POISON_991_…` suffix; if the hook READS `previousSummary` or emits that poison, the measured count betrays it. No vitest file imports this library directly (tests/certification holds only context-harness + rpc-benchmark) — it executes via the `certify-context.mjs` CLI path; recorded here as a coverage caveat, with the two sibling suites GREEN at 16/16.
**Probe:** executed byte-for-byte: `grep -n "CERTIFIED_PI_VERSION = " scripts/certification/pi-compaction.mjs` → :15; `grep -c "previousSummaryReads" scripts/certification/pi-compaction.mjs` → 4 (:83, :86, :104, :106); `grep -n "registerCompactionHook(fakePi" scripts/certification/pi-compaction.mjs` → :79.

## Get live surrounding code
**Retrieve:** executed live against project `pi-fabric`:
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "prepareEligibleCompaction invokeRegisteredFabricCompactor expectedContextEntriesAfterCompaction contextEntriesMatch certified pi version", limit: 6 });
```
(Rank #1–4 resolve `prepareEligibleCompaction` :49-71, `contextEntriesMatch` :117-119, `invokeRegisteredFabricCompactor` :82-108, `expectedContextEntriesAfterCompaction` :110-115 line-exact.)

## Verdict
Adopt the exact-version + function-shape double pin whenever you reach past a dependency's public export map, the honest public/internal capability report, and Proxy-read-counting as the general technique for measuring whether a callback touches forbidden inputs; adapt settings-forced eligibility and the fake-host capture to your plugin surface; omit the poison suffix only when no stale-input channel exists — but keep prior-input detection measured rather than asserted.

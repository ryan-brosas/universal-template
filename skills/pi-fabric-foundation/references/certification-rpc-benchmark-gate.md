<!-- capsule-v2 -->
# Certification benchmark gate — how do you gate a billable real-model A/B benchmark so it skips safely by default, never leaks credentials, and cancels ordering bias with seeded paired runs?

**Source:** pi-fabric MIT `feat/veda-runner@4874ac3abefab27ee0064a3c8571ee017ceb3115`; Codebase Memory `pi-fabric`. **Question:** how does an offline repo ship a cost-incurring live-model benchmark that CI can run blind, and how do you compare three arms fairly on small samples?

## Strict LF-JSONL reader + fail-closed env gate + FNV/xorshift paired orders + Wilson intervals
**Path/Symbol:** `scripts/certification/rpc-lib.mjs` whole (163L): `LfJsonlParser` (:3-38), `positiveNumber/positiveInteger` (:40-48), `benchmarkGate` (:50-77), `hashSeed` (:79-86), `pairedOrders` (:88-104), `wilsonInterval` (:106-114), `summarizeBenchmark` (:116-163). Direct tests: `tests/certification/rpc-benchmark.test.ts` whole (88L, 6 tests GREEN via repo vitest).
**Signature:** `new LfJsonlParser(onRecord)` with `push(chunk)/end(chunk?)`; `benchmarkGate(env?): {enabled, reasons[], config}`; `pairedOrders(repeats, seed, variants?): string[][]`; `wilsonInterval(successes, total, z=1.959963984540054): {low, high}`; `summarizeBenchmark(runs, orders, budget): report`.

### Decisive source
```ts
if (env.PI_FABRIC_REAL_RESUME !== "1") reasons.push("PI_FABRIC_REAL_RESUME must equal 1");
// … every missing precondition is pushed; enabled only when reasons is empty
const keyVariable = env.PI_FABRIC_BENCH_KEY_ENV;
if (!keyVariable) reasons.push("PI_FABRIC_BENCH_KEY_ENV is required");
else if (!env[keyVariable]) reasons.push(`credential variable ${keyVariable} is not set`);
// credential VALUE never enters config — only the NAME of the env var holding it
let state = hashSeed(seed);                 // FNV-1a over the seed text
state ^= state << 13; state ^= state >>> 17; state ^= state << 5;   // xorshift32
return (state >>> 0) / 0x1_0000_0000;
// Fisher-Yates shuffle per repeat → deterministic randomized arm order per repeat
```

**Flow:** the parser buffers chunks through `StringDecoder` so multi-byte UTF-8 split across `push()` boundaries reassembles before `JSON.parse`; records split ONLY on `\n` (optional trailing `\r` stripped; U+2028/U+2029 inside strings preserved), a final record without LF flushes at `end()`, malformed JSON throws. The gate enumerates ALL absent preconditions in one call (`reasons[]`), so one misconfigured variable doesn't hide five others; `config.repeats/maxUsd` default to 0 when disabled. Each repeat runs the arms (`baseline`/`fabric`/`pi-vcc`) in a freshly-shuffled but seed-deterministic order, canceling warm-cache/order effects while keeping reruns reproducible. Summaries report Wilson 95% intervals instead of raw pass rates (small samples get honest widths; total=0 degenerates to {low:0, high:1}, never zero-width), plus pairwise win/tie/loss over SHARED repeat ids — a repeat missing one partner is skipped, not counted as a loss.
**Invariant:** the benchmark is invisible to CI by default — `benchmark-real-resume.mjs` exits 0 printing `"skipped": true` when the gate is closed; the credential value can never appear in reports or logs because it is never read into the gate's output (pinned by `expect(JSON.stringify(gate)).not.toContain("not-reported")`); paired orders are a pure function of (repeats, seed) so two operators produce identical schedules.
**Probe:** executed byte-for-byte from `/mnt/hdd/utopia/inspo/pi-fabric`: `grep -c "1.959963984540054" scripts/certification/rpc-lib.mjs` → 1; `grep -n "state ^= state << 13" scripts/certification/rpc-lib.mjs` → 91; `grep -cF 'env[keyVariable]' scripts/certification/rpc-lib.mjs` → 1; suite: `node_modules/.bin/vitest run tests/certification` → 16/16 passed (rpc-benchmark 6).

## Get live surrounding code
**Retrieve:** executed live against project `pi-fabric`:
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "LfJsonlParser benchmarkGate pairedOrders wilsonInterval summarizeBenchmark", limit: 6 });
```
(Rank #1–4 resolve `benchmarkGate` :50-77, `pairedOrders` :88-104, `wilsonInterval` :106-114, `summarizeBenchmark` :116-163 line-exact.)

## Verdict
Adopt the all-reasons fail-closed gate with indirect credential naming (name-not-value), seed-deterministic paired-order shuffling for small-sample A/B comparisons, and Wilson-interval reporting whenever a "did my change help?" claim must survive review; adapt the env-var vocabulary, arm names, and z-value to your host; omit the pi-vcc sentinel arm and the RPC resume fixture — they are this repo's experiment, not the pattern.

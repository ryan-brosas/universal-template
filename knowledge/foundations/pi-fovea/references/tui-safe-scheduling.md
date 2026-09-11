<!-- capsule-v2 -->
# TUI-safe scheduling kernel — how do heavy extraction sweeps share one event loop with a live UI?

**Source:** pi-fovea MIT `DETACHED@217a103`; Codebase Memory `pi-fovea`. **Question:** Pi runs extensions on the single Node event loop that serves the TUI — how do subprocess fan-outs and 100k-node assemblies never freeze input/rendering?

## Global spawn semaphore + order-preserving mapLimit + chunked yields
**Path/Symbol:** `src/core/asyncutil.ts:mapLimit/Semaphore/spawnGate/yieldToLoop/forEachChunked/envInt` (:7-81); consumers `astgrep.ts:runChunked/patternRunAll` (:200-325), `git.ts:gitOut`, `build.ts` batch loops.
**Signature:** `mapLimit(items, limit, fn): Promise<R[]>` (input ORDER preserved); `spawnGate = new Semaphore(SPAWN_CONCURRENCY=3)` shared by ALL ast-grep/git spawns; `forEachChunked(items, batchSize, fn)` yields one macrotask (`setImmediate`) per batch boundary; `envInt(name, dflt, min, max)` parses/clamps env knobs.
**Data Shape:** Env knobs: `FOVEA_SPAWN_CONCURRENCY` 1..32 (default 3), `FOVEA_IO_CONCURRENCY` 4..512 (default 32), `FOVEA_MAX_ROOTS` 1..32 (default 2 — ONE retention budget shared by states/sessions/baselines/config caches so no override leaves hidden retainers).

### Decisive source
```ts
// Pi runs extensions on the single Node event loop that also serves the TUI:
// every long sync IO/CPU stretch freezes the interface. The two fixes are
// (a) never block on one subprocess/file at a time and (b) yield inside
// irreversibly synchronous CPU sweeps so input and rendering keep flowing.
export const yieldToLoop = (): Promise<void> =>
  new Promise((resolve) => setImmediate(resolve));
// Async git plumbing: even a 50ms spawnSync per turn is a hang tax we no longer pay.
export const gitOut = async (root, args, opts) => spawnGate.run(() => new Promise(...execFile...));
// Adaptive chunk splitting on maxBuffer breach:
const adaptive = async (chunk) => {
  const result = await run(chunkArgs(chunk), cwd);
  if (!result.split || chunk.length === 1) return [{ chunk, result }];
  const middle = Math.ceil(chunk.length / 2);
  return Promise.all([adaptive(half1), adaptive(half2)]).flat();
};
```

**Flow:** every child process (ast-grep stages, git probes) enters through ONE semaphore → chunks of ≤160 files fan out concurrently with order preserved (concatenated outline text stays deterministic) → maxBuffer breaches split the chunk in half and retry → CPU-only assembly loops (graph nodes, cache I/O ≥2000 lines or ≥1 MiB batches, snapshot fingerprinting) interleave `yieldToLoop()` so the TUI repaints mid-sweep.
**Invariant:** Concurrency caps are GLOBAL across subsystems (one gate), never per-caller; yields happen INSIDE long sweeps, not between them; availability probing of ast-grep is memoized sticky-success with a 15 s failure TTL so an install mid-session self-heals without reload, deduped by an inflight map.
**Probe:** `tests/sync.test.ts` — "yields while fingerprinting a large baseline" (setImmediate fires during a 600-file snapshot); `tests/report.test.ts` fake-binary failure attribution exercises runChunked error paths; heat/join suites run deterministically under the same gate.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pi-fovea", query: "mapLimit spawnGate forEachChunked yieldToLoop", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-rule kernel (global semaphore + in-sweep yields), order-preserving bounded maps, adaptive chunk splitting, and the single shared root-cache budget. Adapt limits to your host. Omit nothing — this module is already minimal.

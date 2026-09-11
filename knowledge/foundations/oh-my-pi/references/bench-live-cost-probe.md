<!-- capsule-v2 -->
# Incremental JSONL cost probe — live usage totals from an appending transcript without re-reading it

**Source:** oh-my-pi (MIT) `main@96f428097`; Codebase Memory `oh-my-pi`. **Question:** How do you keep realtime token/cost totals for a still-growing JSONL transcript when multiple pollers fire per second and the file can reach multi-GB — without blocking the event loop or OOMing?

## Byte-cursor tail parsing with partial-line carry and oversized-line discard
**Path/Symbol:** `packages/metaharness/src/runner.ts`:`probeTrialCost`/`probeLine`/`CostProbe` (529-635).
**Signature:** `function probeTrialCost(ompLogPath: string): CostProbe | null` — module-level `Map<path, CostProbe>` holds per-transcript parse state; entries are dropped once the trial finishes (`costProbes.delete` in `parseTrial`).
**Data Shape:** probe state = `{ offset: number; remainder: Buffer; discarding: boolean; costUsd; tokIn; tokOut; tokCache }`. Transcript lines are JSON events; usage is read from assistant `message_end` events only (`usage.input + usage.cacheRead`, `usage.output`, `usage.cacheRead`, `usage.cost.total`).

### Decisive source
```ts
if (!probe || size < probe.offset) {
    // New (or truncated/rotated) transcript. Skip a pre-existing giant head.
    probe = {
        offset: Math.max(0, size - COST_PROBE_FIRST_SCAN_BYTES), // 16 MiB
        remainder: Buffer.alloc(0),
        discarding: size > COST_PROBE_FIRST_SCAN_BYTES, // resync to the next full line
        ...
    };
}
...
const nl = data.indexOf(0x0a, start);
if (nl === -1) break;
if (probe.discarding) probe.discarding = false;   // first newline ends discard mode
else probeLine(data.subarray(start, nl).toString("utf8"), probe);
start = nl + 1;
...
probe.remainder = data.subarray(start);
if (probe.remainder.length > COST_PROBE_MAX_LINE_BYTES) { // 4 MiB
    probe.remainder = Buffer.alloc(0);
    probe.discarding = true;
}
```

**Flow:** stat the file → new/shrunk file ⇒ reset probe at `size − 16MiB` in discard-resync mode → open fd and loop 1MiB reads from `offset`: concat leftover `remainder`, split on `\n`, parse each complete line into running totals, carry the trailing partial line as bytes (multi-byte-char safe), drop any single line over 4MiB by entering discard mode until the next newline → return accumulated totals. Both the CLI render loop (~700ms TTY / 10s pipe) and the manager's 2s sync tick call this for every live trial.
**Invariant:** only appended bytes are ever parsed (the cursor makes double-counting impossible); a truncated head is skipped rather than parsed (undercount beats OOM); a partial trailing line is carried as raw bytes until completed; malformed lines are ignored (incomplete writes are normal mid-append). First-sight of an already-huge transcript parses ONLY its tail.
**Probe:** `packages/metaharness/test/runner.test.ts:145-180` — `accumulates usage incrementally across appended transcript writes`: first flush parses one complete event + leaves a partial line; second flush completes it and adds another event; asserts cost 0.75 / tokIn 140 exactly once-counted.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "probeTrialCost CostProbe costProbes probeLine message_end usage", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the whole pattern for any "live progress against an appending log" problem (agent transcripts, training logs, build output): byte offset cursor + byte-carried partial line + bounded first scan + oversized-line discard. Adapt event filtering (here `message_end` assistant usage) and the 16MiB/4MiB constants to your format and memory budget; omit nothing else — the resync/discard logic is the point. Direct test pins incremental accumulation across appends including a mid-write partial line.

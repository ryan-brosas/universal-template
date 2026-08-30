<!-- capsule-v2 -->
# Smoke-probe composition grammar — how do you compose a real-process protocol probe so failures always diagnose, ids never collide, and the success line is machine-scrapable evidence?

**Source:** pi-acp-jetbrain MIT `main@1f0524f777c93c51747c26d24f3609c2a4e6731d`; Codebase Memory `pi-acp`. **Question:** How do you compose a real-process protocol probe over a shared harness so every failure prints a diagnosis, request ids never collide, and the success output is machine-scrapable evidence?

## The majority probe shape (six scripts share it)
**Path/Symbol:** `scripts/smoke-gaps.mjs` (whole, 97L), `scripts/smoke-lifecycle.mjs` (whole, 77L), `scripts/smoke-queue.mjs` (whole, 45L), `scripts/smoke-export.mjs` (whole, 51L), `scripts/smoke-negative.mjs` (whole, 59L), `scripts/smoke-cancel.mjs` (whole, 78L).
**Signature:** module-scope `const h = new SmokeHarness({...}).start()`; `async function fail(err)`; try block of `h.expectResult(id, method, params, opts)` / `h.expectError(...)` / `h.notify(...)` calls with monotonically increasing LITERAL ids (1, 2, 3, …).
**Data Shape:** every `expectResult` gets a distinct literal id — ids are never computed, so a mid-edit insertion cannot silently collide with a later request; the fail helper closes the harness, prints the adapter stderr tail (last 20 lines), and `process.exit(1)`.

### Decisive source
```js
const h = new SmokeHarness().start()

async function fail(err) {
  await h.close().catch(() => {})
  h.removeIsolation()
  console.error(`FAIL smoke-gaps: ${err.message}`)
  if (h.stderr.length) console.error('adapter stderr tail:\n' + h.stderr.slice(-20).join(''))
  process.exit(1)
}

try {
  const init = await h.expectResult(1, 'initialize', { protocolVersion: 1 })
  // …monotonic literal ids 2..11…
  await h.close()
  h.assertExited(0)
  h.removeIsolation()
  assert(!existsSync(h.env.PI_CODING_AGENT_DIR), 'isolated agent dir not removed')
  console.log(`OK smoke-gaps (dist ${h.distHash()}; fork/resume/close/providers/usage; isolation cleaned)`)
} catch (err) {
  await fail(err)
}
```

**Flow:** start harness → initialize → probe-specific requests with literal ids → on success: close, assert exit code 0, verify isolation cleanup, print `OK <probe> (dist <hash>; <evidence>)` → on any throw: the fail helper guarantees close + stderr tail + exit 1. The `OK` line's parenthetical is a CONTRACT: dogfood-report's summaryLine extraction scrapes the first `OK |FAIL ` stdout line, so every probe embeds its evidence (dist hash, counts, latencies) in that exact shape.
**Invariant:** the harness is ALWAYS closed on both paths (success close + fail-helper close); the exit code is driven by `assertExited(0)` plus the OK/FAIL line, never by implicit process status; isolation cleanup is asserted, not assumed (`!existsSync(PI_CODING_AGENT_DIR)`).
**Probe:** `node scripts/smoke-gaps.mjs` → `OK smoke-gaps (dist <12-hex>; fork/resume/close/providers/usage; isolation cleaned)`; failure path prints `FAIL smoke-gaps: <msg>` + stderr tail.

### Phase-budget arithmetic (smoke-cancel)
**Path/Symbol:** `scripts/smoke-cancel.mjs:8-10`.
```js
// The probe's phase budgets (stream start <=30s, prompt settle <=60s, no-late
// window 2s, follow-up <=120s) sum to ~212s worst case, so the harness deadline
// is raised above that; every phase stays individually bounded (F-004, D-1).
const h = new SmokeHarness({ deadlineMs: 240_000 }).start()
```
The global deadline is set ABOVE the sum of all per-phase budgets, so the global bound can never fire before a phase budget — each phase fails with its own precise timeout message instead of an opaque harness-deadline failure.

### Two-harness isolation handoff (smoke-lifecycle)
**Path/Symbol:** `scripts/smoke-lifecycle.mjs:11,44-46`.
```js
const h1 = new SmokeHarness({ cleanupIsolation: false }).start()
// …phase 1: create, seed, list, close…
const h2 = new SmokeHarness({ env: h1.env, isolate: false }).start()
// …phase 2: session/load against the store phase 1 wrote…
h1.removeIsolation()
assert(!existsSync(h1.env.PI_CODING_AGENT_DIR), 'isolated agent dir not removed')
```
Phase 1 keeps the isolated agent dir alive (`cleanupIsolation: false`); phase 2 starts a SECOND adapter process reusing `h1.env` with `isolate: false` and loads the session the FIRST process created. This proves session/load works against a store written by a different adapter process — a cross-process fixture handoff no single-process test can show. Only the final block removes the isolation and asserts it is gone.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-acp", query: "smoke-gaps smoke-lifecycle SmokeHarness expectResult assertExited fail helper monotonic ids", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the composition grammar: literal monotonic ids, a fail helper that closes + prints the stderr tail + exits 1, an OK line whose parenthetical is scrapable evidence, phase budgets summed below the global deadline, and asserted (not assumed) isolation cleanup. Adapt the two-harness handoff to any multi-process fixture story your protocol needs. Omit the specific dist-hash evidence format unless your acceptance reporter scrapes the same shape. Coverage caveat: these composition patterns had ZERO prior leaf citations — the harness kernel capsule owns the API, not how probes compose it; scripts/ plane is now fully cited at this pin (remaining small probes are minimal instances of this grammar).

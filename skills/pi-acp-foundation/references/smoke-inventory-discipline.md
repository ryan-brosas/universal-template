<!-- capsule-v2 -->
# Smoke-inventory discipline — how do you keep a growing smoke fleet honest, with every probe reachable and harness-owned?

**Source:** pi-acp-jetbrain MIT `main@1f0524f777c93c51747c26d24f3609c2a4e6731d`; Codebase Memory `pi-acp`. **Question:** A repo accumulates one-off end-to-end probe scripts (`smoke-*.mjs`) over time. Without a contract, probes get orphaned (no script entry runs them) or start rolling their own timeouts/isolation instead of the shared harness. How do you make the fleet self-auditing in a single fast check?

## Reachability + harness-ownership census over the probe directory
**Path/Symbol:** `scripts/validate-smoke-inventory.mjs` (whole, 40L) — probe enumeration :12-15, per-probe checks :19-27, floor :29-31, exit :33-38; shared kernel `scripts/lib/validate-common.mjs` (whole, 29L) — `createReporter` :14-27, `findSkillFiles` :8-13. Harness kernel itself: `references/acp-smoke-harness.md` (`scripts/lib/acp-smoke.mjs`). Matrix consumer: package.json `smoke:full` (build + all 15 probes chained with `&&`) and `references/dogfood-fresh-host-acceptance.md` (dogfood-report derives its probe list from this same script).
**Signature:** `node scripts/validate-smoke-inventory.mjs [rootDir]` (root defaults to the repo root via `import.meta.url`; read-only).
**Data Shape:** probes = sorted `readdirSync(scripts)` filtered by `/^smoke-[a-z0-9-]+\.mjs$/`; reachability = the literal string `scripts/<name>` appears in `Object.values(pkg.scripts).join('\n')`; harness ownership = file text contains BOTH `"from './lib/acp-smoke.mjs'"` AND matches `/new SmokeHarness\s*\(/`. Reporter emits `[ok] <msg>` / `[fail] <msg>` lines and exposes `failCount` for the exit code.

### Decisive source
```js
for (const f of probes) {
  const rel = 'scripts/' + f
  if (!scripts.includes(rel)) {
    fail(`${rel} is not referenced by any package.json script (reachability)`)
  } else {
    ok(`${rel} reachable via package scripts`)
  }
  const text = readFileSync(join(root, rel), 'utf8')
  if (!text.includes("from './lib/acp-smoke.mjs'") || !/new SmokeHarness\s*\(/.test(text)) {
    fail(`${rel} does not import and construct the shared harness (deadline/isolation ownership)`)
  }
}
if (probes.length < 5) fail(`expected at least 5 smoke probes, found ${probes.length}`)
```

**Flow:** enumerate probe files → for each: (1) reachability check against the concatenated package.json script values (any script may reference it — `smoke`, `smoke:sessions`, `smoke:full`, …), (2) static ownership check that the probe imports AND constructs `SmokeHarness` (the harness owns deadlines, F-027 isolation, redaction, and SIGTERM→SIGKILL shutdown — a probe that rolls its own timers escapes all four); then enforce a fleet floor (≥5 probes so the check can't pass on an emptied directory) and exit 1 iff any failure.
**Invariant:** every file named like a smoke probe is both runnable through package.json AND deadline/isolation-owned by the shared harness; the check is pure-read (no build, no spawn) so it can gate cheaply. The matrix prose elsewhere (e.g. STATUS.md "full smoke matrix 16/16" at v0.0.39) is allowed to rot — the validator's live count (15 at this pin) is the source of truth.
**Probe:** LIVE this pass: `node scripts/validate-smoke-inventory.mjs` → exit 0, `[ok] smoke inventory: 15 probes registered and harness-owned`, "smoke-inventory contract: ok". No direct unit test exists for the validator itself; the negative path (orphaned probe ⇒ fail) is pinned only by the source logic.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-acp", query: "validate-smoke-inventory createReporter smoke probes", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-axis census (reachability via literal path-in-scripts + static harness-construction check), the fleet floor guard, the shared `[ok]/[fail]` reporter kernel whose `failCount` drives the exit code, and the principle that a machine check — not status prose — owns the fleet count. Adapt the probe filename grammar, the harness import marker, and the floor to your fleet. Omit dynamic execution here deliberately: this validator answers "is the fleet wired correctly" in milliseconds; actually running the probes is the dogfood-report job.

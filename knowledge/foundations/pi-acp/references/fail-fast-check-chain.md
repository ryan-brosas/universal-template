<!-- capsule-v2 -->
# Fail-fast check chain — how do you compose repo gates so one command answers "is this tree done?" without hiding later failures?

**Source:** pi-acp-jetbrain MIT `main@1f0524f777c93c51747c26d24f3609c2a4e6731d`; Codebase Memory `pi-acp`. **Question:** A repo accumulates many structural gates (catalog, manifest, routing, fabric, work, notion, hygiene, inventory, whitespace). Running them piecemeal invites drift; running them aggregated hides which one failed. How do you compose them into ONE canonical command with unambiguous failure attribution?

## Ordered gate table, stdio-inherit spawn, immediate exit with the child's own status
**Path/Symbol:** `scripts/check.mjs` (whole, 33L) — gate table :3-13, spawn loop :15-25, final ok :27; `.github/workflows/check.yml` (whole, 40L) — step order :20-33, local-smoke comment :34-35.
**Signature:** `node scripts/check.mjs` (no args; runs from the repo root; spawns children with `stdio: 'inherit'` so each gate's own `[ok]`/`[fail]`/`[skip]` lines stream straight through).
**Data Shape:** the gate table is an ordered array of `[command, args]` tuples: skill-packs → sync-skill-manifest --check → probe-skill-routing → pi-fabric → work-management → notion-workspace → release-hygiene → smoke-inventory → `git diff --check`.

### Decisive source
```js
// :15-25 fail-fast loop — the child's own status IS the exit status
for (const [command, args] of checks) {
  console.log(`\n> ${command} ${args.join(' ')}`)
  const result = spawnSync(command, args, { cwd: process.cwd(), stdio: 'inherit' })
  if (result.error) {
    console.error(result.error.message)
    process.exit(1)
  }
  if (result.status !== 0) process.exit(result.status ?? 1)
}
console.log('\nrepository check: ok')
```

## Flow
1. Gates run in a fixed order; each prints its own diagnostics (inherited stdio) under a `> <command>` banner, so failure attribution is always visible.
2. First nonzero child status exits IMMEDIATELY with that status — no aggregation, no continuation; a spawn error (binary missing) exits 1.
3. The chain ends on `git diff --check` (whitespace/conflict-marker hygiene) — the last word on tree cleanliness belongs to git itself.
4. CI runs this exact command (`check.yml` step `node scripts/check.mjs`) BEFORE test/lint/typecheck/build, on a Node 20+24 matrix; the full smoke matrix stays deliberately local (comment: it spawns the `pi` binary and makes real model calls, which GitHub runners do not provision).
5. The same command string is pinned in the fabric runtime config (`trustedCommands.canonical-check`) and in prose needles (AGENTS template `[verified check command]`, init prompt "one canonical completion command") — three planes, one contract (see pi-fabric-config-gate).

## Invariant
- Exactly ONE canonical completion command; humans, CI, and agent runtime config must all resolve to it.
- Fail-fast with inherited stdio: you always see WHICH gate failed and its own output, but you do NOT see later gates' results — a mid-chain crash HIDES downstream gates (live: on a checkout with a partial gitignored `.pi/`, work-management's ENOENT crash aborts the chain at gate 5, so notion/release-hygiene/smoke-inventory never run; in CI, where `.pi` is absent entirely, all gates skip cleanly and the chain reaches `repository check: ok`).
- Cheap structural gates run before expensive behavioral suites — fail in milliseconds, not minutes.
- The full behavioral smoke matrix is intentionally NOT in the canonical command: it needs a model-backed `pi` binary; the canonical command must run everywhere.

## Probe
No direct unit test exists for check.mjs at this pin (recorded caveat). Executed live probe:
```
node scripts/check.mjs
# → gates 1-4 print [skip] exit 0 (deepest-path gates on a checkout without .pi/skills|fabric.json)
# → gate 5 validate-work-management: [fail] lines, then unhandled ENOENT at :83 → exit 1
# → chain ABORTS; gates 6-9 never run; exit 1
```

## Retrieve
`search_graph(project="pi-acp", q="check.mjs canonical completion command spawnSync fail-fast", mode="ids")` — revalidate at the current pin (graph unavailable passes 5–8; direct read is the authority).

## Adopt/Adapt/Omit Verdict
**Adopt.** Adopt: one ordered gate table as the single completion command; stdio-inherit fail-fast spawning that preserves the child's own exit status and diagnostics; cheap structural gates before expensive suites; keeping behavioral/model-backed suites OUT of the canonical command with the reason recorded where CI can see it. Adapt: if you need every gate's result on failure, aggregate instead of fail-fast — but then attribute failures per gate in the summary; this repo chose fail-fast and accepts hidden downstream gates on mid-chain crash. Omit: nothing structural.

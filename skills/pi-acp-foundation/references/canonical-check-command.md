<!-- capsule-v2 -->
# Canonical completion command — how do you give a repository exactly ONE completion command that humans, CI, and agent runtime config all agree on?

**Source:** pi-acp-jetbrain MIT `main@1f0524f777c93c51747c26d24f3609c2a4e6731d`; Codebase Memory `pi-acp`. **Question:** A repo accumulates many checks (structural gates, tests, lint, typecheck, build, smoke). Without one canonical entry point, "is this tree done?" has no single answer, and the prose that tells agents what "done" means rots independently of the machine that enforces it. How do you make ONE command the completion contract across all three planes?

## Ordered fail-fast gate chain pinned in three planes
**Path/Symbol:** `scripts/check.mjs` (whole, 33L) — gate table :4-14, spawn loop :16-28, final ok :30; `.github/workflows/check.yml` (whole, 40L) — matrix :14-18, step order :20-33, local-smoke comment :34-35; cross-pins in `scripts/validate-pi-fabric.mjs` §1 :38-48 (trustedCommands.canonical-check), §5-6 :113-140 (prose needles + CI check).
**Signature:** `node scripts/check.mjs` (no args; runs from the repo root; read-only except nothing — pure spawn).
**Data Shape:** the gate table is an ordered array of `[command, args]` tuples: `[node validate-skill-packs] → [node sync-skill-manifest --check] → [node probe-skill-routing] → [node validate-pi-fabric] → [node validate-work-management] → [node validate-notion-workspace-skill] → [node validate-release-hygiene] → [node validate-smoke-inventory] → [git diff --check]`. Each spawns with `stdio: 'inherit'`; a nonzero child status exits IMMEDIATELY with that child's own status (fail-fast, no aggregation); a spawn error (`result.error`) exits 1. The last gate is `git diff --check` (whitespace/conflict-marker hygiene) — the chain ends on git itself.

### Decisive source
```js
const checks = [
  [process.execPath, ['scripts/validate-skill-packs.mjs']],
  [process.execPath, ['scripts/sync-skill-manifest.mjs', '--check']],
  [process.execPath, ['scripts/probe-skill-routing.mjs']],
  [process.execPath, ['scripts/validate-pi-fabric.mjs']],
  [process.execPath, ['scripts/validate-work-management.mjs']],
  [process.execPath, ['scripts/validate-notion-workspace-skill.mjs']],
  [process.execPath, ['scripts/validate-release-hygiene.mjs']],
  [process.execPath, ['scripts/validate-smoke-inventory.mjs']],
  ['git', ['diff', '--check']]
]
for (const [command, args] of checks) {
  const result = spawnSync(command, args, { cwd: process.cwd(), stdio: 'inherit' })
  if (result.error) { console.error(result.error.message); process.exit(1) }
  if (result.status !== 0) process.exit(result.status ?? 1)
}
```

**Flow:** the same command string is pinned in THREE planes simultaneously: (1) the CI workflow runs `node scripts/check.mjs` as the FIRST quality step, before `npm test` / `lint` / `typecheck` / `build` (Node matrix 20+24); (2) the fabric runtime-config contract requires `schema.trustedCommands.canonical-check` to be exactly `node scripts/check.mjs` with `shell !== true` and `timeoutMs === 120000` (validate-pi-fabric §1); (3) the PROSE contract requires the AGENTS template to contain `[verified check command]` and the init prompt to contain `one canonical completion command` (validate-pi-fabric §5-6), plus the existence of both `scripts/check.mjs` and the CI workflow running it (§6). If any plane drifts, the fleet's own validator fails.
**Invariant:** there is exactly one canonical completion command; its identity is enforced by machine config, prose needles, AND the CI workflow at once, so no plane can rename or fork it silently. Structural gates run before behavioral ones; the full smoke matrix is deliberately EXCLUDED from CI (check.yml comment: it spawns the `pi` binary and makes real model calls, which GitHub runners do not provision — run `smoke:full` locally before release). Each dev-tree gate self-skips when its target dir is absent, so the same command passes in CI (no `.pi/`) and in a dev tree (full `.pi/`).
**Probe:** LIVE this pass: `node scripts/check.mjs` on THIS checkout → exit 1 (the work-management gate crashes on the partial local `.pi/` tree — see release-hygiene-tracked-scan.md for the crash class); in CI the same command passes because `.pi/` is gitignored and absent. No direct unit test exists for check.mjs; its contract is pinned by validate-pi-fabric's trustedCommands + prose needles (source-read confirmed).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-acp", query: "check.mjs canonical-check trustedCommands validate", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the ordered fail-fast tuple table (child exit status propagates verbatim; no result aggregation — the first failure IS the report), the terminal `git diff --check`, and the three-plane pinning of the command identity (runtime config + prose needles + CI workflow all checked by the fleet's own validators). Adapt the gate order to your subsystems (pure-read structural gates first, expensive behavioral gates last, smoke excluded from CI when it needs host binaries or model calls). Omit the specific gate list — it is this repo's operating layer. Caveat: the self-skip design makes the canonical command's outcome TREE-DEPENDENT (pass in CI, fail on a dev host with a partial state dir) — the skip-gate granularity must match each gate's deepest touched path or the canonical command inherits the crash (see release-hygiene-tracked-scan.md live finding).

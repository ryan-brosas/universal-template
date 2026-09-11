<!-- capsule-v2 -->
# Pi-fabric three-plane config gate — how do you pin one completion contract in machine config, prose, and CI simultaneously?

**Source:** pi-acp-jetbrain MIT `main@1f0524f777c93c51747c26d24f3609c2a4e6731d`; Codebase Memory `pi-acp`. **Question:** A repo's completion contract ("what does done mean, and which command proves it") lives in three places that drift independently: the agent runtime's machine config, the prose documents agents read, and CI. How do you pin all three to agree — structurally, without running the agent?

## One contract, three pinned planes, plus moved-path and stale-wording guards
**Path/Symbol:** `scripts/validate-pi-fabric.mjs` (whole, 156L) — config plane :13-51, prose plane :53-89 + :106-136, CI plane :138-148, moved-path guards :91-104, gitignore guard :150-153, deepest-path skip :14-17.
**Signature:** `node scripts/validate-pi-fabric.mjs [root]` (default root = repo root; shared `createReporter` from `scripts/lib/validate-common.mjs` drives exit code).
**Data Shape:** `.pi/fabric.json` is a JSON config: `{fullCodeMode: boolean, executor: {memoryLimitBytes: number}, schema: {mode: 'enforce'|'audit', trustedCommands: {'canonical-check': {command, args, shell, timeoutMs}}}, agents?: {runner?}}`. Prose planes are needle lists checked with `includes`.

### Decisive source
```js
// :38-46 the canonical-check contract, pinned byte-exact in machine config
if (
  cc.command === 'node' &&
  Array.isArray(cc.args) &&
  cc.args.join(' ') === 'scripts/check.mjs' &&
  cc.shell !== true &&
  cc.timeoutMs === 120000
)
  ok('schema.trustedCommands.canonical-check = node scripts/check.mjs')
else fail('schema.trustedCommands.canonical-check must run node scripts/check.mjs without a shell for 120000ms')
// :97-103 moved-path guard requires the NEW path to exist on disk
for (const ref of [
  '.pi/skills/pack-delivery/test-driven-development/SKILL.md',
  '.pi/skills/verification-before-completion/SKILL.md'
]) {
  if (ship.includes(ref) && existsSync(join(root, ref))) ok('ship.md skill exists: ' + ref)
  else fail('ship.md skill missing or not referenced: ' + ref)
}
```

## Flow
1. Skip gate on `.pi/fabric.json` (:14-17) — the DEEPEST path this gate touches — so dev trees without fabric config `[skip]` exit 0 cleanly (contrast: validate-work-management gates on `.pi` but touches `.pi/templates` and crashes).
2. Config plane: `fullCodeMode === true`; `executor.memoryLimitBytes === 4294967295` (the QuickJS heap ceiling — smaller values make the guest reject the config); `schema.mode` ∈ {enforce, audit}; `trustedCommands['canonical-check']` must be exactly `node scripts/check.mjs`, `shell !== true`, `timeoutMs === 120000`; `agents.runner` must NOT be pinned in project config (host-selectable).
3. Prose plane: AGENTS.md must contain `schema.hypothesize`/`schema.verify`/`schema.commit`/`canonical-check`/`[DONE:n]`; mutating prompts (create/fix/init/plan/ship) must contain the Schema-loop needles + "do not mutate" and must NOT contain the stale word "prewalk"; the agents template must carry the golden-rule heading + `[verified check command]` placeholder; the init prompt must demand "one canonical completion command".
4. Moved-path guards: ship.md must NOT reference the OLD TDD path (`.pi/skills/test-driven-development/...`) and MUST reference the NEW pack-delivery path — with `existsSync` proving the new target is real on disk, so a rename can't leave prose pointing at a ghost.
5. CI plane: `scripts/check.mjs` exists; `.github/workflows/check.yml` contains `node scripts/check.mjs`.
6. Gitignore plane: `.gitignore` must contain `.veda/` (local Veda session state is host data, never tracked).

## Invariant
- The SAME command string (`node scripts/check.mjs`) is pinned in three independent planes; any plane drifting fails the gate — prose, config, and CI cannot silently disagree about "done".
- Trusted commands run without a shell (`shell !== true`) and with an explicit timeout — the runtime-config twin of the argv-array discipline.
- Absence checks ("prewalk", old TDD path) pin vocabulary retirements; presence+existsSync checks pin vocabulary introductions.
- Deepest-path skip granularity: gate on the deepest path you actually read, and the same command is safe in dev tree, published checkout, and CI.

## Probe
No direct unit test exists for this script at this pin (recorded caveat). Executed live probe:
```
node scripts/validate-pi-fabric.mjs
# → [skip] .pi/fabric.json is not in this checkout; fabric contract checks run in the development tree
# → exit 0
```

## Retrieve
`search_graph(project="pi-acp", q="validate-pi-fabric trustedCommands canonical-check fullCodeMode memoryLimitBytes", mode="ids")` — revalidate at the current pin (graph unavailable passes 5–8; direct read is the authority).

## Adopt/Adapt/Omit Verdict
**Adopt.** Adopt: the three-plane contract pinning (machine config + prose needles + CI) with byte-exact command equality; moved-path guards that require the new path to exist on disk; stale-wording absence checks; deepest-path skip granularity; "never pin the agent runner in project config" as a host-selection boundary. Adapt: the specific QuickJS ceiling and fabric schema are host-specific values — port the PATTERN (pin the exact trusted command, no shell, explicit timeout), not the numbers.

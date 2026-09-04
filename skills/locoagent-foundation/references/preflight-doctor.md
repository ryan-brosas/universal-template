<!-- capsule-v2 -->
# Preflight doctor with critical/non-critical checks — how does one exit-code health check tell an operator what is broken without failing on warnings?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** How should a bring-up preflight script classify checks so a missing optional pin warns while a broken dedup log fails the whole run?

## Check accumulator with per-check criticality and self-testing probes
**Path/Symbol:** `scripts/doctor.ts`:`Check` interface (`:16`), `add` accumulator (`:18-19`), CDP-pin cross-validation (`:62-88`), operation-log round-trip (`:98-117`), report loop + exit code (`:139-147`). Top-level script (no function nodes in the graph — retrieve via the `Check` anchor).
**Signature:** `add(name: string, ok: boolean, critical: boolean, detail: string): void`; CLI `bun run doctor [--check-cdp]`.
**Data Shape:** `Check { name, ok, critical, detail }` accumulated module-level; output rows are `OK `/`!! `/`XX `-prefixed lines; process exits 1 iff any check that is both `!ok && critical`.

### Decisive source
```ts
// Operation-log round-trip (isolated temp log; never touches persona/)
{
  const dir = mkdtempSync(join(tmpdir(), 'loco-doctor-'))
  const logPath = join(dir, 'op.json')
  const script = join(root, 'scripts', 'log-operation.ts')
  const env = { ...process.env, LOCO_OP_LOG_PATH: logPath }
  const url = 'https://example.com/doctor-probe'
  const a = Bun.spawnSync([process.execPath, 'run', script, 'add',
      '--platform', 'doctor', '--action', 'probe', '--url', url, '--status', 'success'], ...)
  const c = Bun.spawnSync([process.execPath, 'run', script, 'check',
      '--platform', 'doctor', '--action', 'probe', '--url'], ...)
  const ok = (a.exitCode ?? 1) === 0 && (c.exitCode ?? 1) === 0 // check exits 0 = done
  rmSync(dir, { recursive: true, force: true })
  add('Operation-log round-trip', ok, true, ok ? 'write+check OK' : 'failed')
}
...
let failed = false
for (const c of checks) {
  const mark = c.ok ? 'OK ' : c.critical ? 'XX ' : '!! '
  if (!c.ok && c.critical) failed = true
  console.log(`${mark} ${c.name.padEnd(26)} ${c.detail}`)
}
console.log(failed ? 'DOCTOR: critical checks FAILED' : 'DOCTOR: all critical checks passed')
process.exit(failed ? 1 : 0)
```

**Flow:** accumulate checks (Bun runtime → host detect → device resolve → Chrome binary → agent-browser on PATH → CDP pin vs registry default port → `.env` exists → persona dir optional → **live round-trip** of the dedup CLI against a temp log via `LOCO_OP_LOG_PATH` isolation) → optionally probe every registered platform's CDP port when `--check-cdp` is passed → print aligned `OK/!!/XX` rows → exit non-zero only for failed *critical* checks. The pin check cross-validates two sources of truth: the pinned `agent-browser` config must equal the DEFAULT platform's port read from the targets registry (`targets['x'] ?? first`, falling back to 9222 so doctor still answers without a registry).
**Invariant:** Optional-but-important checks (`CDP pin`, `.env`, persona dir, per-platform CDP reachability) are `critical: false` — they mark `!!` and NEVER flip the exit code; only structural failures do. The round-trip check must run against an isolated temp path (`LOCO_OP_LOG_PATH`), never the real `persona/operation-log.json` — a diagnostic must not mutate production state. Every failure detail carries the fix command ("run: bun run setup-chrome").
**Probe:** No upstream test file for doctor.ts (it IS the test harness). Deterministic source-grounded probes: the exit rule at `doctor.ts:141-147`, isolation env var at `:99-102`, pin cross-check at `:66-87`. Coverage caveat recorded; port with your own smoke test asserting `XX` rows ⇒ exit 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "doctor preflight health critical check", limit: 10 });
```
Graph anchors: `scripts.doctor.Check` (:16); companion `scripts/lib/browser-targets.healthCheck` (:135-143) covers the per-target CDP probe.

## Verdict
Adopt the three-state marking (ok/warn/fail), critical-only exit gating, isolated-path self-tests of your own CLIs inside preflight, and fix-command-in-detail messages. Adapt the specific check list to your host. Omit interactive onboarding prompts — this doctor is deliberately non-interactive and safe under cron.

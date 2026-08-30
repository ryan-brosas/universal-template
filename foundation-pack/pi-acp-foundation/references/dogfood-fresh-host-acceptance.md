<!-- capsule-v2 -->
# Dogfood fresh-host acceptance — how do you produce fresh-host acceptance evidence headlessly when half the acceptance can only be observed inside a real IDE chat?

**Source:** pi-acp-jetbrain MIT `main@1f0524f777c93c51747c26d24f3609c2a4e6731d`; Codebase Memory `pi-acp`. **Question:** A published adapter must be accepted on a FRESH host (new IDE chat, new PID, current bundle), but the executor running the checks is headless and cannot see the IDE. How do you split acceptance into headless-verifiable checks vs host-only items, and make the exit code honest about which half is missing?

## Headless checks + recorded-unavailable host items + warn-gated exit
**Path/Symbol:** `scripts/dogfood-ide.mjs` (whole, 113L) — launch-path check :31-49, process classification :52-72, host-only records :74-86, checklist write :88-106, exit contract :108-113; `scripts/lib/adapter-process.mjs` (whole, 4L) — `isAdapterProcessArgs`; `scripts/dogfood-report.mjs` (whole, 119L) — probe derivation :15-25, build-first :27-39, redaction :41-47, probe loop :49-60, report :62-100. Campaign work record dir `.pi/work/close-dogfood-findings-f008-f033/` (gitignored). Findings ledger: STATUS.md F-numbers (F-033 fresh-host acceptance, F-008 stale bundle, F-009 remote checkout, F-030 inspection evidence, F-016/F-032 report).
**Signature:** `node scripts/dogfood-ide.mjs` (no args; reads `~/.jetbrains/acp.json`, `dist/index.js`, `ps -eo pid,etimes,args`); `isAdapterProcessArgs(args: string): boolean`; `node scripts/dogfood-report.mjs` (rebuilds dist, runs every `smoke:full` probe, writes versioned JSON+MD).
**Data Shape:** findings are `{kind: 'ok'|'warn'|'todo'|'unavailable', message}` where message ALWAYS passes `redact` (repo root → `<repo>`, home → `<home>`). dogfood-report results are `{probe, ok, exitCode, signal, durationMs, summary, stderrTail}` with summary = first stdout line matching `/^OK |^FAIL /`, stderrTail = last 5 stderr lines, both through `REDACT_RE` (sk-/ghp_/github_pat_/AKIA/Bearer/key=value credential shapes) + path redaction; report schema `pi-acp.dogfood-report.v1` carries `build.distSha256` + `build.buildRevision` (extracted from the first OK summary via `/build ([0-9a-f]{6,})/`).

### Decisive source
```js
// P1-6 audit: warn findings (missing config, remote/stale adapter PIDs) mean
// acceptance is incomplete — a green exit would be false confidence. The F-033
// checklist todo is host-only and does not fail the run.
const warnCount = findings.filter(f => f.kind === 'warn').length
if (warnCount > 0) {
  console.error(`dogfood-ide: ${warnCount} warn finding(s) — fresh-host acceptance incomplete (nonzero exit)`)
  process.exit(1)
}
```
```js
// Stale/remote adapter processes vs the dist build time. etimes is elapsed
// seconds since process start, robust to locale/date formatting.
const ps = spawnSync('ps', ['-eo', 'pid,etimes,args'], { encoding: 'utf8', timeout: 10_000 })
// ... per line: if (!isAdapterProcessArgs(args)) continue
// remote = !args.includes(root)            -> F-009 warn "different checkout"
// startedMs < distMtime.getTime()          -> F-008 warn "stale bundle"
```
```js
// dogfood-report: probes come FROM the matrix, never a hand-kept list
const full = pkg.scripts['smoke:full'] ?? ''
const probes = full.split('&&').map(s => s.trim())
  .filter(s => s.startsWith('node scripts/smoke-')).map(s => s.replace(/^node /, ''))
// P1-6 audit: dogfood must exercise a fresh build — previously the build step was
// filtered out and a stale dist could report green. Build once, then probe.
```

**Flow:** dogfood-ide: (1) parse `~/.jetbrains/acp.json`; at least one `agent_servers` entry whose `command args` join contains `dist/index.js` must reference THIS checkout (else warn: new chats may load a published package); (2) enumerate processes, keep only adapter-looking args, classify each as remote-checkout / stale-before-dist-mtime / fresh-ok using `etimes` elapsed seconds; (3) append the host-only F-033 runbook as `todo` and the headless limitation as `unavailable` WITH reasons; (4) write timestamped `fresh-host-checklist.md` into the campaign work record; (5) exit 1 iff any `warn`. dogfood-report: derive probes from `smoke:full`, `npm run build` FIRST (fail ⇒ exit 1), hash the fresh dist, run each probe with a 240s timeout capturing outcome/duration/summary/stderr-tail, write `dogfood-report-<stamp>.{json,md}`, exit = failures ? 1 : 0.
**Invariant:** the exit code can only be 0 when every HEADLESS check passed — host-only items may be outstanding (`todo`/`unavailable` never fail the run) but any `warn` (stale or remote adapter PID, missing/mismatched agent entry) forces nonzero, so a green dogfood run can never claim full fresh-host acceptance that wasn't observed. Evidence files are machine-redacted before writing (paths + credential shapes), and the report's probe list is derived from `smoke:full` so it cannot drift from the matrix.
**Probe:** `test/unit/dogfood-ide-process.test.ts` (2 tests: recognizes checkout `/work/pi-acp/dist/index.js` + installed `pi-acp`/`npx pi-acp-jetbrain`; ignores unrelated commands inside a checkout like `scripts/auto-commit.mjs`). LIVE this pass: `node scripts/dogfood-ide.mjs` → exit 1 with 4 warns — including a FALSE POSITIVE class the test does not pin: other packages' `dist/index.js` processes (context7-mcp, deepwiki-mcp under npx cache) match `isAdapterProcessArgs` and surface as F-009 "different checkout" warns. The matcher trades precision for recall; the warn channel absorbs the noise.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-acp", query: "isAdapterProcessArgs dogfood-ide etimes stale bundle", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the kind-typed finding model (`ok/warn/todo/unavailable`) with the warn-gated exit as the honesty contract for split headless/host acceptance, the `etimes`-based staleness comparison against artifact mtime (locale-proof), recording unavailable host items WITH reasons instead of skipping them, deriving the report's probe list from the canonical matrix script, build-before-probe, and pre-write redaction of paths + credential shapes. Adapt the agent-config path (`~/.jetbrains/acp.json`), the campaign work-record dir, and the F-number annotations to your findings ledger. Omit the loose `*/dist/index.js` matcher unless you accept its false positives on hosts running other dist-bundled node tools — tighten it (e.g. require the checkout root or package name in args) if your warn channel feeds automation. dogfood-report full execution rebuilds dist and runs the whole smoke fleet (minutes); source-read suffices to port the contract.

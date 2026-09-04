<!-- capsule-v2 -->
# Repo-contributed inspection scripts — how do you let the REPO extend a post-turn lint pass without hardcoding rules in the adapter?

**Source:** pi-acp-jetbrain MIT `main@1f0524f777c93c51747c26d24f3609c2a4e6731d`; Codebase Memory `pi-acp`. **Question:** How does an adapter expose a repo-owned extension point for custom lint rules (Kotlin inspection scripts) with deterministic discovery, a global call budget, and bounded diagnostics when a script or its result is malformed?

## Discovery contract + budgeted KTS pass
**Path/Symbol:** `src/acp/ide-inspection.ts` — `discoverInspectionScripts` (:326-349), `summarizeMalformedRaw` (:161-169), `runKtsInspections` (:362-450), constants :8-16 (`KTS_SCRIPT_DIR='inspections'`, `KTS_SCRIPT_SUFFIX='.inspection.kts'`, `DEFAULT_MAX_KTS_SCRIPTS=8`, `DEFAULT_MAX_KTS_CALLS=120`, `MAX_KTS_SCRIPT_BYTES=64*1024`, `KTS_RETRY_DELAY_MS=1000`, `RAW_DIAGNOSTIC_MAX_CHARS=400`). Companion funnel in `references/post-turn-inspection-gate.md`.
**Signature:** `export function discoverInspectionScripts(cwd: string, maxScripts = 8): IdeKtsScript[]` where `IdeKtsScript = { path: string; code: string }`; `export function summarizeMalformedRaw(raw: unknown, maxChars = 400): string`; `export async function runKtsInspections(opts: { bridge: InspectionBridge; cwd: string; files: string[]; timeoutMs: number; maxCalls?: number }): Promise<KtsPassResult | null>` where `KtsPassResult = { summaries: IdeKtsSummary[]; truncated: boolean; fileProblems: Map<string, IdeInspectionProblem[]> }`.
**Data Shape:** discovery reads ONLY `<cwd>/inspections/`, regular files ending `.inspection.kts`, name-sorted (deterministic run order), capped at 8; each script is read, trimmed, and SKIPPED when >64KB or unreadable; missing directory → `[]` (never throws). Per-script summary `{ scriptPath, status: 'ok'|'compile-error'|'error'|'malformed', filesRun, problems, message? }`. The KTS pass returns `null` when the bridge lacks `run_inspection_kts` (caller omits the `kts` report field entirely).

### Decisive source
```ts
// Retry consumes a budget slot: the check runs AFTER incrementing, so the LAST
// slot can never be retried — malformed there is annotated, not re-called.
calls += 1
// ... first call + normalize ...
if (outcome.status === 'malformed') {
  if (calls >= maxCalls) {
    outcome = { status: 'malformed', problems: [],
      message: `malformed result, no retry budget — raw: ${summarizeMalformedRaw(raw)}` }
  } else {
    calls += 1
    await new Promise(resolve => setTimeout(resolve, KTS_RETRY_DELAY_MS))
    const retryRaw = await bridge.callRemoteTool('run_inspection_kts', {...}, timeoutMs)
    outcome = normalizeKtsResult(retryRaw)
    if (outcome.status === 'malformed')
      outcome.message = `malformed result after retry — raw: ${summarizeMalformedRaw(retryRaw)}`
  }
}
// per-script status only ESCALATES: ok(0) < malformed(1) < error(2) < compile-error(3)
if (statusRank[outcome.status] > statusRank[entry.status]) entry.status = outcome.status
```

**Flow:** gate (see companion capsule) collects changed files → `runKtsInspections` gates on `bridge.hasRemoteTool('run_inspection_kts')` → discovers scripts (sorted, capped, oversize/unreadable skipped) → nested loop file×script under ONE global call budget (default 120); each call sends `{ inspectionKtsCode, contextPath: file, projectPath: cwd }`; results normalize via the compile-success envelope (`compilationSuccess:false` → `compile-error` with first non-empty detail line sliced to 300 chars; `compilationSuccess:true` + `foundProblems[]` → problems with `highlightType` folded to error/warning via `ktsSeverity`); malformed → one-shot retry after 1000ms only while budget remains; thrown calls → per-script `error` status; budget exhaustion sets `truncated=true` and the caller appends a synthetic `{ scriptPath:'(truncated)', status:'error' }` summary. Problems merge into the report's per-file items; every failure degrades to a summary line, never an exception.
**Invariant:** discovery order is name-sorted so multi-script repos run identically across machines; the retry can never exceed the global budget (the post-increment check makes the last slot non-retriable); per-script status is monotone-escalating so one good file cannot hide a later compile error; `summarizeMalformedRaw` must survive circular/undefined payloads (JSON.stringify in try/catch with `String()` fallback) and is always length-capped at 400 chars so a hostile tool response cannot blow up the report.
**Probe:** `node --import tsx --test test/unit/ide-inspection.test.ts` — "discovers sorted *.inspection.kts scripts and skips other files" pins sort order + suffix gate + non-script exclusion; "returns [] when the inspections directory is missing"; "records compile errors as a diagnostic without failing the inspection" pins compile-error status + first-line-only detail + "custom inspections degraded" summary; "degrades when a KTS call throws and keeps built-in findings" pins error-status-with-message while built-in findings survive.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-acp", query: "discoverInspectionScripts summarizeMalformedRaw runKtsInspections", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the filesystem extension-point contract (fixed dir + fixed suffix + sorted + capped + size-gated discovery), the single global call budget shared across file×script pairs, the budget-aware one-shot retry, monotone status escalation, and the try/catch JSON diagnostic summarizer. Adapt the script language/suffix to your host's scripted-lint surface (or drop the whole seam — the built-in lint path works without it). Omit the IntelliJ-specific `run_inspection_kts` argument shape (`inspectionKtsCode`/`contextPath`) unless your IDE exposes the same remote tool. Direct tests executed green at the pin; end-to-end proof exists in `scripts/smoke-ide-inspect.mjs` (repo `inspections/no-any.inspection.kts` discovered, invoked over the changed file, `kts[0].status==='ok'` asserted in the persisted report).

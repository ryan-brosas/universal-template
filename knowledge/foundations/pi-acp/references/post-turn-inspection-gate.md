<!-- capsule-v2 -->
# Deterministic post-turn IDE inspection gate — how do you run the host IDE's own diagnostics over a turn's changes without ever failing the turn?

**Source:** pi-acp-jetbrain MIT `main@1f0524f777c93c51747c26d24f3609c2a4e6731d`; Codebase Memory `pi-acp`. **Question:** How does an adapter invoke remote IDE lint tools adapter-side (not through the agent), normalize their wildly varying result shapes, and bound every dimension of the pass?

## Never-throws inspection funnel with schema'd report
**Path/Symbol:** `src/acp/ide-inspection.ts` whole file (`runEnforcedInspection` :511-609, `normalizeInspectionResult` :246-269, `unwrapToolResult` :214-239, `runKtsInspections` :362-450, `writeReport` :485-503, `inspectionSummary` :612-619) + `src/acp/mcp-bridge.ts` (`hasRemoteTool`, `callRemoteTool`, `#findTool`) + agent-side driver `enforceIdeInspection` in `src/acp/agent.ts` (:1062-1096).
**Signature:** `export async function runEnforcedInspection(opts: RunEnforcedInspectionOptions): Promise<IdeInspectionOutcome>`; `async callRemoteTool(name: string, args: Record<string, unknown>, timeoutMs?: number): Promise<unknown>`; outcome = `{ status:'inspected', report: IdeInspectionReport, reportPath?: string } | { status:'skipped', reason: string }`.
**Data Shape:** report schema literal `'pi-acp.ide-inspection.v1'`; bounds `DEFAULT_MAX_FILES=200`, `DEFAULT_TIMEOUT_MS=30_000`, KTS `maxScripts=8 / maxCalls=120 / 64KB per script / 1000ms retry delay`, raw diagnostic capped at 400 chars. Files list = git-status ∪ turn-touched paths, exclusion prefixes `node_modules/ dist/ .git/ .pi/ inspections/`.

### Decisive source
```ts
// #findTool resolves by EXPOSED name first, then scans remoteName — the inspection
// gate addresses tools by their REMOTE name (lint_files) not the ide_<srv>_<tool> exposure.
#findTool(name: string): BridgeTool | undefined {
  const byExposed = this.#tools.get(name)
  if (byExposed) return byExposed
  for (const tool of this.#tools.values()) {
    if (tool.remoteName === name) return tool
  }
  return undefined
}
```

**Flow:** env kill-switch `PI_ACP_ENFORCE_IDE_INSPECT === '0'` → skip; no bridge or neither `lint_files` nor `get_file_problems` in catalog → `{status:'skipped'}` with reason; no changed files → skipped. Prefer ONE batched `lint_files {files, min_severity:'warning', projectPath}` call; else fan out per-file `get_file_problems {filePath, errorsOnly:false}` via Promise.all. Result normalization ladder: MCP wrapper unwrap (`structuredContent` first, else content-text blocks joined and JSON-parsed) → array | `{items|results|files|problems|issues}` envelope | single-file shape (`{filePath, errors:[...]}`); problem severity from `severity ?? level`, kept only when present. Then optional repo-owned Kotlin scripts under `<cwd>/inspections/*.inspection.kts`: sorted discovery, per-file × per-script calls with a GLOBAL budget, malformed results retried ONCE when budget remains (delay 1000ms) else annotated with truncated raw payload, worst-status wins per script (`ok < malformed < error < compile-error`), truncation appends a synthetic `'(truncated)'` error summary. Problems merge into items, JSON+Markdown reports persist under `.pi/work/ide-inspections/<sessionId>/<ISO-stamp>.{json,md}` (dir override `PI_ACP_IDE_INSPECT_DIR`), one-line chat summary emitted as an agent_message_chunk. EVERY failure path degrades to skipped/diagnostic — the gate never throws into the turn.
**Invariant:** the bridge call runs on the BRIDGE's own connection (`callRemoteTool`), NOT through pi IPC, so it works while pi is idle/mid-turn; severity classification is regex-based (`/error/i`, `/warn/i`) so IntelliJ's varied severity strings fold correctly; `errors`/`warnings` counts are derived at report time, never trusted from the tool payload.
**Probe:** `npx tsx --test test/unit/ide-inspection.test.ts` (normalization matrix, merge precedence, KTS budgets/retry).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-acp", query: "runEnforcedInspection normalizeInspectionResult runKtsInspections", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the adapter-side direct-call seam (bypassing the agent loop), the unwrap→envelope→single-file normalization ladder, the global KTS call budget with one-shot retry, and the never-throw degrade-to-skipped contract with a versioned on-disk report. Adapt tool names, report location, and severity regexes to your IDE. Omit the KTS script concept unless your host has an equivalent scripted-inspection surface. Direct tests executed green at the pin.

<!-- capsule-v2 -->
# Gate-time inspection skip contract — how do you design a never-throws post-turn gate whose skip reasons stay observable?

**Source:** pi-acp-jetbrain MIT `main@1f0524f777c93c51747c26d24f3609c2a4e6731d`; Codebase Memory `pi-acp`. **Question:** An enforced post-turn inspection gate must never break the turn — but a gate that silently skips is indistinguishable from a gate that never ran. How do you enumerate skip branches, keep the reason observable, and what breaks diagnosis when the caller discards it?

## Four ordered skip branches, remote-name tool matching, and a discarded-reason observability gap
**Path/Symbol:** `src/acp/ide-inspection.ts` `runEnforcedInspection` :505-550 — no-bridge :513, tools-unavailable :515-518, no-changed-files :525, call-failure :547-550; `collectChangedFiles` :88-112; `mergeInspectFiles` :120-146; `src/acp/agent.ts` `enforceIdeInspection` :1059-1095 + prompt tail :1041-1046; `src/acp/mcp-bridge.ts` `hasRemoteTool` :665-667 + `#findTool` :694-700; `src/acp/session.ts` `touchedFilePaths` :327, :776-778.
**Signature:** `runEnforcedInspection(opts: {bridge?: InspectionBridge | null, cwd, sessionId, outputDir?, maxFiles?, maxKtsCalls?, timeoutMs?, extraFiles?: string[]}): Promise<{status: 'inspected', report, reportPath?} | {status: 'skipped', reason: string}>` — never throws.
**Data Shape:** the skip reason is a free-form string surfaced at `_meta.piAcp.inspection.{status, reason}` on the PromptResponse; four canonical reasons: `'no IDE MCP bridge'`, `'IDE inspection tools (lint_files/get_file_problems) unavailable'`, `'no changed files to inspect'`, `'IDE inspection failed: <msg>'`.

### Decisive source
```ts
// ide-inspection.ts:511-525 — the four ordered skip branches
if (!bridge) return { status: 'skipped', reason: 'no IDE MCP bridge' }
const hasLint = bridge.hasRemoteTool('lint_files')
const hasProblems = bridge.hasRemoteTool('get_file_problems')
if (!hasLint && !hasProblems) {
  return { status: 'skipped', reason: 'IDE inspection tools (lint_files/get_file_problems) unavailable' }
}
// …
const files = mergeInspectFiles(opts.cwd, gitFiles, opts.extraFiles ?? [], maxFiles)
if (files.length === 0) return { status: 'skipped', reason: 'no changed files to inspect' }
// mcp-bridge.ts:694-700 — #findTool matches exposedName OR remoteName
#findTool(name: string): BridgeTool | undefined {
  const byExposed = this.#tools.get(name)
  if (byExposed) return byExposed
  for (const tool of this.#tools.values()) {
    if (tool.remoteName === name) return tool
  }
  return undefined
}
```

## Flow
1. Turn ends with `end_turn` → `enforceIdeInspection(session)` (agent.ts:1041); `PI_ACP_ENFORCE_IDE_INSPECT=0` disables entirely (:1064).
2. Branch order: bridge present? → tools present? → changed files present? → call succeeds? Any failure degrades to `skipped` + reason; the turn NEVER breaks.
3. Tool presence is checked by REMOTE name (`lint_files`), resolved through `#findTool` which matches the exposed `ide_<server>_<tool>` name OR the raw remote name — so the check is name-collision-tolerant, but it can only see tools already registered in the adapter's catalog.
4. Changed files = git status (`collectChangedFiles`, exclusion prefixes node_modules/dist/.git/.pi/inspections, existsSync-filtered) MERGED with `session.touchedFilePaths` (edit/write tool paths captured at session.ts:776-778) via `mergeInspectFiles` — the gate still fires after the auto-commit watcher swept the tree clean.
5. Outcome lands in `_meta.piAcp.inspection` (agent.ts:1045) and a summary is surfaced as an `agent_message_chunk` (:1073-1081); internal errors become a stderr diagnostic and `null` (:1082-1090).

## Invariant
- The gate is total: every failure mode maps to a typed skip reason, never an exception through the turn path.
- Server-side `tools/list` receipt does NOT prove adapter-side catalog registration — discovery is async, and `#addTools` can drop tools (denylist, truncation, schema widening) after the server answered; `hasRemoteTool` is the only gate-time truth.
- **Observability gap (live, 7 reproductions):** `scripts/smoke-ide-inspect.mjs` asserts `_meta` only AFTER the `waitForLog('lint_files invocation')` that throws — on failure the catch path prints `err.message` + stderr tail, and the skip reason that would identify the branch in one run is discarded. `PI_ACP_DEBUG_BRIDGE=1` dumps descriptors at session/new only (agent.ts:176), not gate-time catalog state. A one-line `_meta` dump in the smoke's catch would resolve the branch immediately — upstream fix, outside lane authority.
- Skip reasons are part of the contract: enumerate them exhaustively and assert on them in tests, or your e2e harness learns nothing from failure.

## Probe
Direct tests: `test/unit/ide-inspection.test.ts` (22/22 GREEN at this pin, pass 5) and `test/unit/gate-hardening.test.ts` (12/12 GREEN) pin the funnel and skip branches at unit level. Live e2e probe (7th reproduction, this pass):
```
node scripts/smoke-ide-inspect.mjs
# → FAIL smoke-ide-inspect: timed out waiting for lint_files invocation
#   adapter stderr tail: session/new mcpServers … (descriptor dump only — no gate-time state)
# → exit 1 (host blocker persists; unit suites green)
```

## Retrieve
`search_graph(project="pi-acp", q="runEnforcedInspection skipped reason hasRemoteTool lint_files", mode="ids")` — revalidate `runEnforcedInspection`/`hasRemoteTool` at the current pin (graph unavailable passes 5–8; direct read is the authority).

## Adopt/Adapt/Omit Verdict
**Adopt.** Adopt: the never-throws gate with an exhaustive typed skip-reason taxonomy; remote-name tool matching tolerant of exposure renaming; git-status + turn-touched-paths merge so the gate survives tree-sweeping watchers. Adapt: make the skip reason ASSERTABLE in your e2e harness (print `_meta` on failure) — this repo's own smoke discards it, which is the cautionary half of the pattern. Omit: the IDE-specific tool names and report layout.

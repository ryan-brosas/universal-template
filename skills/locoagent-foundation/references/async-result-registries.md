<!-- capsule-v2 -->
# Async-result registries — how do fire-and-forget background processes deliver their output into the NEXT turn exactly once?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** What is the shared register/check/deliver contract for async hook processes and LSP diagnostics, and what does each do about dedup, volume, and cleanup?

## AsyncHookRegistry + LSPDiagnosticRegistry (twin pattern)
**Path/Symbol:** `src/utils/hooks/AsyncHookRegistry.ts` (:1-309); `src/services/lsp/LSPDiagnosticRegistry.ts` (:1-387). Producers: `registerPendingAsyncHook` (:30-83) / `registerPendingLSPDiagnostic` (:65-85). Consumers: `checkForAsyncHookResponses` (:113-268) / `checkForLSPDiagnostics` (:193-338). Drained by attachment collectors `getAsyncHookResponseAttachments` / `getLSPDiagnosticAttachments` in src/utils/attachments.ts.
**Signature:** register: `(payload) => void` keyed by processId (async hooks, module-level `Map<string, PendingAsyncHook>`) or randomUUID per notification (LSP, `Map<string, PendingLSPDiagnostic>`); check: `() => Promise<Response[]>` (hooks, allSettled) / `() => Response[]` (LSP, synchronous — "diagnostics arrive synchronously").
**Data Shape:** both carry a boolean gate on the entry (`responseAttachmentSent` / `attachmentSent`) so delivery is at-most-once; async entries hold the live `ShellCommand` + a `stopProgressInterval` closure.

### Decisive source
```ts
// AsyncHookRegistry.checkForAsyncHookResponses — snapshot, probe, THEN mutate:
const hooks = Array.from(pendingHooks.values())
const settled = await Promise.allSettled(hooks.map(async hook => {
  if (!hook.shellCommand) { hook.stopProgressInterval(); return { type: 'remove' } }
  if (hook.shellCommand.status === 'killed') { ...cleanup(); return { type: 'remove' } }
  if (hook.shellCommand.status !== 'completed') return { type: 'skip' }
  // parse stdout lines: FIRST line starting '{' that parses AND lacks 'async'
  // → sync response; break. Then: hook.responseAttachmentSent = true
}))
// allSettled — isolate failures so one throwing callback doesn't orphan
// already-applied side effects (responseAttachmentSent, finalizeHook)
```

**Flow (async hooks):** hook process prints JSON to stdout → next turn's collector polls → completed shells get their first non-`async` JSON line extracted as the response → mark sent → `finalizeHook` (stop progress interval, drain stdout/stderr, shell cleanup, emitHookResponse with outcome success/error by exit code) → delete from map. Killed shells are removed+cleaned; missing shell commands removed; empty-stdout completed shells removed WITHOUT response. SessionStart completions trigger `invalidateSessionEnvCache()` AFTER the loop (:257-262).
**Flow (LSP):** publishDiagnostics notifications accumulate → check collects ALL unsent files across servers → within-batch dedup by content key `{message,severity,range,source,code}` per URI PLUS cross-turn dedup against an LRU(500 files) of delivered keys → severity sort (Error<Warning<Info<Hint) → volume caps 10/file, 30 total → survivors recorded into the delivered LRU → single merged result `{serverName: joined names, files}` → pending entries deleted ("tracked in deliveredDiagnostics LRU for dedup, so we don't need to keep them in pendingDiagnostics after delivery" :229-231).
**Invariant:** (1) MARK-AFTER-COLLECT ordering: dedupe/limit FIRST, flip the sent flag only after the batch survived processing (LSP marks after successful dedup; async hooks set `responseAttachmentSent` only once a real response was parsed) — marking before processing loses data on failure paths; (2) dedup failures DEGRADE to delivering duplicates, never dropping ("Include the diagnostic anyway to avoid losing information" :176-178, fallback `dedupedFiles = allFiles` :222-226); (3) file EDITS clear the cross-turn LRU for that file (`clearDeliveredDiagnosticsForFile`) while session reset clears everything — plain shutdown clears ONLY pending ("Does NOT clear deliveredDiagnostics" :343-344); (4) one hook's rejection must not orphan another's applied side effects ⇒ allSettled with post-loop mutation.
**Probe:** coverage caveat (no upstream tests). Deterministic probes: `grep -n "MAX_DIAGNOSTICS_PER_FILE\|MAX_TOTAL_DIAGNOSTICS\|MAX_DELIVERED_FILES" src/services/lsp/LSPDiagnosticRegistry.ts` → 10/30/500 constants; `grep -n "allSettled\|orphan" src/utils/hooks/AsyncHookRegistry.ts`; `sed -n '183,212p' src/utils/hooks/AsyncHookRegistry.ts` pins the JSON-line scan verbatim; `sed -n '340,344p' src/services/lsp/LSPDiagnosticRegistry.ts` pins the asymmetric-clear doc comment.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "checkForLSPDiagnostics dedup diagnostics", limit: 5, fields: ["signature","name","file"] });
// → src/services/lsp/LSPDiagnosticRegistry.ts 193-338 rank #1; twin: registerPendingAsyncHook
```

## Verdict
Adopt the register→poll→mark-once→delete lifecycle and degrade-open dedup; adapt payload shapes; omit the progress-interval plumbing if your host has no streaming UI. Porting traps: deleting registry entries before their content is durably recorded (loses events on crash between mark and yield); clearing the cross-turn dedup on every turn (re-delivers identical diagnostics forever).

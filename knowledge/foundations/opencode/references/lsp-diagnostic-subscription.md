<!-- capsule-v2 -->
# LSP diagnostic subscription — how do you wait for diagnostics from heterogeneous language servers (push-only, pull-only, multi-identifier) without blocking on the slowest one?

**Source:** opencode MIT `dev@03521003fafd`; Codebase Memory `opencode`. **Question:** After a file mutation the agent wants fresh diagnostics before reporting to the model. Some servers push (publishDiagnostics), some pull (textDocument/diagnostic per identifier), some do both, and registrations arrive dynamically mid-session. A naive "wait for everything" blocks on the slowest identifier; a naive "wait for the first" misses related-file findings. What is the wait contract?

## Dual push/pull caches + capability tracking
**Path/Symbol:** `packages/opencode/src/lsp/client.ts` (constants :13-18, state :141-165, publishDiagnostics handler :166-177, register/unregisterCapability :196-215, `documentPullState` :355-365, `workspacePullState` :367-377).
**Signature:** `create({serverID, server, root, directory, instance}) → Promise<Info>`; `Info = {root, serverID, connection, notify.open, diagnostics: Map<path, Diagnostic[]>, waitForDiagnostics({path, version, mode?, after?}), shutdown}`.
**Data Shape:** pushDiagnostics + pullDiagnostics = two independent `Map<path, Diagnostic[]>`; published = `Map<path, {at: number, version?: number}>`; diagnosticRegistrations = `Map<id, {id, method, registerOptions?}>` filtered to textDocument/diagnostic.

### Decisive source
```ts
// client.ts:166-177 — push handler records freshness; typescript seeds on FIRST push
connection.onNotification("textDocument/publishDiagnostics", (params) => {
  const filePath = getFilePath(params.uri)
  if (!filePath) return
  published.set(filePath, { at: Date.now(), version: typeof params.version === "number" ? params.version : undefined })
  if (shouldSeedDiagnosticsOnFirstPush(input.serverID) && !pushDiagnostics.has(filePath)) {
    pushDiagnostics.set(filePath, params.diagnostics); return   // TS pushes aggressively on first open
  }
  updatePushDiagnostics(filePath, params.diagnostics)
})
// client.ts:355-377 — pull support = static capability OR dynamic registration, split by scope
const documentRegistrations = [...diagnosticRegistrations.values()].filter(
  (registration) => registration.registerOptions?.workspaceDiagnostics !== true)
return { documentIdentifiers: [...new Set(...)], supported: hasStaticPullDiagnostics || documentRegistrations.length > 0 }
```

**Flow:** merged view = dedupe(push ∪ pull) per path, dedupe key JSON of {code, severity, message, source, range}. The initialize handshake (45s timeout → InitializeError) deliberately does NOT overclaim: workspace.diagnostics.refreshSupport=false and textDocument.publishDiagnostics.versionSupport=false (test pins both). workspace/configuration answers one result per requested item with dotted-section traversal, missing → null. didOpen sets version 0 and CLEARS both caches for the path (fresh open invalidates stale data); didChange on an existing file does NOT clear — comment pins clangd re-emitting only on real content change, so clearing would lose errors on no-op touchFile; it bumps version+1 and sends a single full-range change when syncKind===incremental(2), else a full-text change. shutdown() ends+disposes the connection then Process.stop's the child.

**Invariant:** a path's reported diagnostics are always the deduped union of both caches; a re-open resets history, a touch does not; the client never claims capabilities it will not honor.
**Probe:** `packages/opencode/test/lsp/client.test.ts` (read whole, 488L): "initialize does not overclaim unsupported diagnostics capabilities" pins refreshSupport/versionSupport false via captured initialize params; "workspace/configuration returns one result per requested item" pins `[{beta:1}, 1, null, initialization]`; "sends ranged didChange for incremental sync servers" pins version 1 + single range (0,0)→(1,0) with new text; "document mode falls back to push diagnostics" pins zero pull requests when only push exists. Source pin:
```bash
grep -n 'DIAGNOSTICS_DEBOUNCE_MS = ' packages/opencode/src/lsp/client.ts        # expect 1 (:13, 150)
grep -n 'INITIALIZE_TIMEOUT_MS = ' packages/opencode/src/lsp/client.ts          # expect 1 (:18, 45_000)
grep -n 'shouldSeedDiagnosticsOnFirstPush' packages/opencode/src/lsp/client.ts  # expect 2
```

## Parallel identifier pulls with early unblock
**Path/Symbol:** `packages/opencode/src/lsp/client.ts` (`requestDiagnostics` :388-410, `requestDocumentDiagnostics` :416-427, `requestFullDiagnostics` :429-444, `waitForFreshPush` :464-497, `waitForDocumentDiagnostics` :499-519, `waitForFullDiagnostics` :521-541, `mergeResults` :272-292).
**Signature:** `waitForDiagnostics({path, version, mode: "document"|"full", after?})`; document timeout 5s, full timeout 10s, per-pull request timeout 3s, push debounce 150ms.
**Data Shape:** DiagnosticRequestResult = `{handled, matched, byFile: Map<path, Diagnostic[]>}`; handled = the server answered, matched = the CURRENT file got an entry.

### Decisive source
```ts
// client.ts:388-410 — dispatch ALL pulls in parallel, resolve as soon as done(results) is true
return new Promise((resolve) => {
  let pending = requests.length; let resolved = false
  const finish = (merged, force = false) => {
    if (resolved) return
    if (!force && !done(results)) return      // early unblock: one batch already has current-file diags
    resolved = true; resolve(merged)
  }
  for (const request of requests) request.then((result) => {
    results.push(result); pending -= 1
    const merged = mergeResults(filePath, results)
    finish(merged)
    if (pending === 0) finish(merged, true)   // slow pulls still merge in before final resolve
  })
})
// client.ts:412-414 — the latency contract
// LATENCY-CRITICAL: dispatch identifier pulls in parallel and unblock once one batch already produced
// diagnostics for the current file. Let slower pulls keep merging in the background; do not sequence
// identifier-by-identifier, and do not add a post-match settle/debounce delay. See PR #23771.
```

**Flow:** waitForDocumentDiagnostics loops under the 5s budget: pull all identifiers in parallel → return if matched; else race three signals — a FRESH push (version-aware: a push whose version differs from the requested one is ignored unless newer; debounced 150ms after the last push), a registration CHANGE (a new identifier appeared → loop again), or timeout (exit). Only a registration change continues the loop. Full mode additionally pulls workspace/diagnostic reports (related files land in their own cache entries) and treats ANY handled response as sufficient (an empty workspace report is "handled", test pins <1s). mergeResults inserts an explicit [] for the matched-but-empty current file so "server answered, no errors" is distinguishable from "never answered".

**Invariant:** the wait never exceeds its mode budget; it never sequences identifiers; a match on the current file unblocks immediately while slower pulls keep merging; a push older than the requested version cannot satisfy the wait; registration churn is the only signal that justifies another pull round.
**Probe:** client.test.ts "document mode waits for pull diagnostics" pins a registered identifier producing the only diagnostic (request count > 0); "document mode does not wait for the slowest pull identifier after current-file diagnostics arrive" pins <1s with a 2.5s-slow second identifier AND request count > 1 (both dispatched); "full mode includes workspace pull diagnostics" pins related-file entries landing in the cache; "full mode treats an empty workspace pull response as handled" pins <1s on an empty report; "document mode accepts matching push diagnostics published before waiting" pins pre-wait pushes resolving fast. Source pin:
```bash
grep -n 'LATENCY-CRITICAL' packages/opencode/src/lsp/client.ts   # expect 1 (:412)
grep -n 'Do not wipe diagnostics on didChange' packages/opencode/src/lsp/client.ts  # expect 1 (:564)
```

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "LSPClient waitForDiagnostics requestDiagnostics waitForFreshPush documentPullState workspacePullState publishDiagnostics", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the dual-cache (push/pull) union-with-dedupe as the diagnostic model — servers disagree about who reports what, and the consumer must not care. Adopt parallel-dispatch-with-early-unblock as the wait kernel: fan out every known pull, resolve on the first current-file match, let stragglers merge, and make registration-change the ONLY loop-continue signal (push arrival or timeout exits). Adopt version-aware push freshness — a timestamp alone lets a stale push satisfy a wait for a newer edit. Adopt the explicit-empty-on-match rule so "no errors" is a positive answer. Adapt the mode budgets (5s/10s/3s/150ms) to your latency targets; omit the typescript first-push seed unless you integrate a server that front-loads its first push. Direct test read whole (client.test.ts 488L); bun runner blocked at this checkout (no node_modules), probes are byte-exact greps.

<!-- capsule-v2 -->
# Test harness — the mock-ExtensionAPI + temp-dir + execFile-swap pattern that makes a pi extension unit-testable without qmd, an LLM, or real memory files

**Source:** pi-memory (MIT) `main@39e6b998a2279c8fad4a2c6c64e26828c1d6023e`; Codebase Memory `pi-memory` (full mode 380n/941e @2026-08-22T23:46:09Z). **Question:** How do you test a coding-agent memory extension end-to-end at tool granularity with zero external dependencies (no LLM, no qmd binary, no network), so every seam stays behavior-pinnable?

## Test harness
**Path/Symbol:** `test/unit.test.ts:createMockPi` (:76–90), `createMockCtx` (:93–103), `createShutdownCtx` (:105–124), `setupTmpDir` (:63–66), `cleanupTmpDir` (:68–73); source seams `_setBaseDir`/`_resetBaseDir` (`index.ts:67–78`), `_setExecFileForTest`/`_resetExecFileForTest`, `_setQmdAvailable`, `_clearUpdateTimer`/`_getUpdateTimer`, `_clearEmbedInFlight`/`_getEmbedInFlight`, `_resetMemorySnapshot`.
**Signature:** `registerExtension(pi)` against `pi = { registerTool(toolDef){tools[toolDef.name]=toolDef}, on(event,handler){hooks[event]=handler} }`; tools invoked as `await tool.execute(callId, params, null, null, ctx)`.
**Data Shape:** ctx = `{ sessionManager: { getSessionId: () => sid }, hasUI, ui: { notify } }` (shutdown variant adds `getBranch()`, `model`, `modelRegistry`). The exec swap is a full `execFile` replacement `(file, args, opts, cb) => void` capturing `calls: string[][]` and invoking `cb(err, stdout, stderr)` manually.

### Decisive source
```ts
// createMockPi (76-90): capture the registration surface, never run it
const pi = {
	registerTool(toolDef) { tools[toolDef.name] = toolDef; },
	on(event, handler) { hooks[event] = handler; },
};
// cleanupTmpDir (68-73): EVERY teardown resets module-global state in a fixed order,
// because index.ts keeps paths/qmd/timers/snapshot in module scope
function cleanupTmpDir() {
	_resetBaseDir(); _setQmdAvailable(false); _clearUpdateTimer();
	fs.rmSync(tmpDir, { recursive: true, force: true });
}
```

**Flow:** (1) Each test redirects all paths into a fresh `mkdtempSync` via `_setBaseDir` — no test ever touches real `~/.pi/agent/memory`. (2) `createMockPi` registers into plain records so tests can call `tools.X.execute(...)` / `hooks.y(...)` directly. (3) Every qmd interaction is faked by swapping the module's `execFileFn` (`_setExecFileForTest`) and asserting on the captured argv (e.g. `[["update"],["embed"]]`). (4) Teardown restores base dir, qmd flag, timers, and deletes the temp tree.

**Invariant:** the production module must expose its three mutable planes (paths, process spawn, module-global caches) as swappable seams or none of this is testable; teardown must reset ALL of them or state bleeds across tests.

**Probe:** EXECUTED this pass at HEAD: `bun test test/unit.test.ts` → **182 pass / 0 fail / 438 expect() calls** in 1.3s (scratch copy of the repo, deps installed; suite touches only temp dirs).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-memory", query: "createMockPi setupTmpDir cleanupTmpDir _setExecFileForTest", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the mock-API-capture + temp-dir + exec-swap triad and the fixed-order teardown for any file-backed agent extension. Adapt the exported underscore test hooks to your module's actual global state. Omit nothing — this is the portability core that made all other capsules probeable.
---

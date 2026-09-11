<!-- capsule-v2 -->
# Custom tool loading contracts — how do you load user-supplied tool modules into a name-collision-safe registry with injected dependencies?

**Source:** oh-my-pi (MIT) `main@2b66ee69f249`; Codebase Memory `oh-my-pi`. **Question:** What is the load pipeline for third-party tool files so they never depend on workspace module resolution, never shadow built-ins, and can be re-bound per session?

## Connected graph-selected seam
**Path/Symbol:** `packages/coding-agent/src/extensibility/custom-tools/loader.ts` (:1-301 whole): `loadTool` :55-109, `CustomToolLoader` :126-195, `discoverCustomToolPaths` :238-272; adapter `custom-tools/wrapper.ts:CustomToolAdapter`; direct test `test/extensibility/custom-tool-loader.test.ts`.
**Signature:** `new CustomToolLoader(pi, cwd, builtInToolNames, pushPendingAction?)`; `load(pathsWithSources: ToolPathWithSource[])`; `setUIContext(ui, hasUI)` live-swap.
**Data Shape:** factory returns one tool or an array; per item `{ name, label?, description, parameters, execute }`; errors accumulate as structured `{ path, error, source? }`, never thrown.

### Decisive source
```ts
// Dependencies are injected through CustomToolAPI so tools loaded from user
// directories do not depend on workspace module resolution.
if (resolvedPath.endsWith(".md") || resolvedPath.endsWith(".json")) {
	return { tools: [], errors: [{ path: toolPath,
		error: "Declarative tool files (.md, .json) cannot be loaded as executable modules", source }] };
}
this.#seenNames = new Set<string>(builtInToolNames);   // built-ins pre-seed the registry
if (this.#seenNames.has(loadedTool.tool.name)) {       // conflict -> structured error, skip
	this.errors.push({ path: toolPath, error: `Tool name "${loadedTool.tool.name}" conflicts with existing tool`, source });
	continue;
}
```
**Flow:** discoverCustomToolPaths (capability providers -> plugin tree -> configured paths; dedupe by resolved path, carrying source metadata) -> loadCustomTools per session -> import + factory call under withHostGuard -> array/single normalize -> per-item shape guard -> first-wins name registration -> wrap via CustomToolAdapter (applyToolProxy forwarding). Subagent rule: forward collected PATHS (`preloadedCustomToolPaths`), then re-run loadCustomTools so factories re-bind to the subagent-scoped API (cwd/exec/pushPendingAction/UI) — forwarding bound instances would close over the parent session.
**Invariant:** (1) user-dir tools resolve deps only through the injected API; (2) built-ins are unshadowable (seeded set, first-wins); (3) UI context is mutable AFTER load via shared-API swap; (4) sibling extension loader uses the same discover/load split with the complementary ordering rule: imports concurrent, factory binding SEQUENTIAL in path order for deterministic last-wins registration (`extensions/loader.ts:loadExtensions` docstring :552-587).
**Probe:** `test/extensibility/custom-tool-loader.test.ts`: writes temp tool sources and asserts valid-tool loads, `[null]` arrays produce invalidToolError, mixed arrays keep the valid item, name-conflict errors; plus `toolWireSchema`/`validateToolArguments` round-trip through arktype parameters.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "CustomToolLoader discoverCustomToolPaths", limit: 10 });
```

## Verdict
Adopt: injected-API loading, seeded first-wins name registry, declarative-file rejection with explicit errors, discover/load split for child sessions. Adapt: your capability-provider names; pending-action plumbing optional. Omit: Bun file API in manifest reading.

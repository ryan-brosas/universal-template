<!-- capsule-v2 -->
# Hybrid grep router — how do you augment native search with graph navigation without breaking either?

**Source:** pi-fovea MIT `DETACHED@217a103`; Codebase Memory `pi-fovea`. **Question:** Replacing grep breaks hosts that depend on exact line matches; ignoring the graph wastes semantic navigation — what routes a query between them, and what happens on graph failure?

## Query-shape classification + fallback ladder + augment middleware
**Path/Symbol:** `src/index.ts:isSymbolLikeGrepQuery/requestsNativeGrep/registerGrepOverride/tool_result middleware` (:43-205).
**Signature:** `isSymbolLikeGrepQuery(pattern): boolean`; `requestsNativeGrep(params): boolean`; modes `off | replace | augment(default)` via `tools.grepMode` (legacy `replaceGrep` boolean migrates, explicit mode wins — see config capsule sibling seam in tests/config.test.ts).
**Data Shape:** Symbol-like = no regex metacharacters, OR qualified symbol (`a.b.c`, `a::b`), OR repo path, OR route path (`/x/y`). Native-requesting = any of path/glob/ignoreCase/literal/context/limit options present, or regex-meta pattern that is NOT qualified/path/route.

### Decisive source
```ts
// Augment mode (default): native grep keeps core semantics in EVERY host
// (pi's model-facing loop AND pi.grep inside fabric_exec, which re-emits
// the lifecycle for nested core tools), and Fovea appends a graph section
// to symbol-query results through tool_result middleware. Never throws:
// a broken or seedless graph simply yields native grep unchanged.
pi.on("tool_result", async (event, ctx) => {
  if (event.toolName !== "grep" || event.isError) return undefined;
  if (!pattern || !isSymbolLikeGrepQuery(pattern)) return undefined;
  const result = await focus(ctx.cwd, pattern, cfg.tools.grepAugmentBudget, { fresh: true });
  if (Number(result.details.seeds ?? 0) === 0) return undefined;  // miss → native untouched
  ...append text(gap + result.text.replace(/^fovea focus/, "fovea graph"))...
});
// Replace-mode override execute(): graph backend broken must not break search:
catch (error) {
  const native = createGrepTool(root);
  const fallback = await native.execute(id, params, signal, onUpdate);
  return { ...fallback,
    content: [text(`fovea graph unavailable — native text results (${message})\n`), ...fallback.content],
    details: { ..., backend: "native", foveaError: message } };
}
```

**Flow:** classify query → augment: run native grep, then append a fresh budgeted focus view when seeds > 0 (one blank line padded regardless of native block termination) → replace: bare symbol queries navigate the graph; misses fall back to native lines; errors degrade to native WITH a one-line note marking results native → off: never registered. Mode change requires extension reload so pi and pi-fabric capture identical behavior.
**Invariant:** Native grep semantics are preserved in every host and on every failure; graph sections are additive and clearly labeled; seedless queries append NOTHING (no noise); the middleware returns `undefined` (not a rewritten event) whenever it doesn't contribute.
**Probe:** `tests/settings.test.ts` (grepMode plumbing through settings save/reload) + `tests/config.test.ts` migration cases; `tests/extension.test.ts` exercises the registered grep TOOL end-to-end without a live host: "uses Fovea only for bare grep symbol queries" (:253 — symbol/qualified/route queries all route through the graph), "skips augmentation for regex patterns, errors, non-grep tools, and off/replace modes", "augment mode swallows graph failures so native grep passes through untouched", "degrades bare-query grep to native text with a note when the graph backend errors", "co-existence: native grep results gain a Fovea graph section for symbol queries" — direct behavioral coverage, caveat narrowed to the pi session-middleware wiring only.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pi-fovea", query: "grepMode augment requestsNativeGrep registerTool", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt query-shape routing, the never-throw fallback ladder with labeled degradation, and append-only augmentation through result middleware. Adapt the classifier regexes to your tool grammar. Omit the pi-specific `createGrepTool` host import.

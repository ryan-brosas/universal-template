<!-- capsule-v2 -->
# Incremental build kernel — how does `build()` stay cheap across rebuilds without ever removing utilities?

**Source:** tailwindcss MIT `main@90f8ff41c8e2a4d17bc76921e23e9d672123da76`; Codebase Memory `tailwindcss`. **Question:** When a watcher feeds new candidates on every rebuild, which states allow returning the previous output untouched, and what must be spliced when they fail?

## compileAst → build closure
**Path/Symbol:** `packages/tailwindcss/src/index.ts:714-820` (`compileAst`, inner `build`), `packages/tailwindcss/src/index.ts:824-860` (`compile` wrapper).
**Signature:** `compileAst(input: AstNode[], opts): Promise<{ sources, root, features, build(candidates: string[]): AstNode[] }>`; `build` mutates the captured `ast`/`utilitiesNode` in place.
**Data Shape:** closure state: `allValidCandidates: Set<string>`, `compiled: AstNode[] | null` (memoized optimized AST), `previousAstNodeCount`, `defaultDidChange` (from `inlineCandidates`), plus `designSystem.invalidCandidates`.

### Decisive source
```ts
// Add all new candidates unless we know that they are invalid.
let prevSize = allValidCandidates.size
for (let candidate of newRawCandidates) {
  if (!designSystem.invalidCandidates.has(candidate)) {
    if (candidate[0] === '-' && candidate[1] === '-') {
      let didMarkVariableAsUsed = designSystem.theme.markUsedVariable(candidate)
      didChange ||= didMarkVariableAsUsed
      didAddExternalVariable ||= didMarkVariableAsUsed
    } else {
      allValidCandidates.add(candidate)
      didChange ||= allValidCandidates.size !== prevSize
    }
  }
}
// If no new candidates were added, we can return the original CSS. This
// currently assumes that we only add new candidates and never remove any.
if (!didChange) { compiled ??= optimizeAst(ast, designSystem, opts.polyfills); return compiled }
...
if (!didAddExternalVariable && previousAstNodeCount === newNodes.length) { ... return compiled }
utilitiesNode.nodes = newNodes
compiled = optimizeAst(ast, designSystem, opts.polyfills)
```

**Flow:** (1) `features === Features.None` → return input CSS unchanged. (2) No `utilitiesNode` → static stylesheet; memoize one `optimizeAst` result forever. (3) Merge candidates: candidates starting with `--` are *used external variables*, not classes → `theme.markUsedVariable`; others join the accumulate-only set. (4) Set-size unchanged and no newly-used variable → reuse memoized compiled AST. (5) Recompile all valid candidates, splice into `utilitiesNode.nodes`; if node count is identical and no variable flipped → still reuse. (6) Else re-optimize whole AST.
**Invariant:** The candidate set only ever grows within one compiler instance; removal support would invalidate tiers 4–5. Tier 5's "same node count ⇒ same output" assumes a recompile that yields the same number of nodes produced the same nodes — true because compilation is deterministic per candidate set.
The `compile()` string wrapper adds an object-identity guard: if `api.build()` returns the same AST reference, it returns the cached CSS string instead of re-serializing (`index.ts:841-852`).
**Probe:** `packages/tailwindcss/src/index.test.ts:87` "`@tailwind utilities` is only processed once" — two `@tailwind utilities` directives yield exactly one copy of `.flex`/`.grid`. Also :109 pins default-theme utility emission.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "tailwindcss", query: "compileAst build utilitiesNode optimize incremental candidates", filePattern: "packages/tailwindcss/src/*", limit: 10, fields: ["lines"] });
```
Observed top hit: `compileAst … src/index.ts 714-820`, then `build … src/index.ts 841-852`.

## Verdict
Adopt the three-tier short-circuit ladder, accumulate-only candidate semantics, and `--var`-candidate-as-used-variable channel. Adapt `optimizeAst`/polyfill selection to your host's output targets. Omit the version banner injection and PostCSS-migration error export (`postcssPluginWarning`) — packaging behavior, not compiler contract.

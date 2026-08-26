<!-- capsule-v2 -->
# Design-system memo lattice — how does one DesignSystem object memoize parse/compile work without leaking invalid results?

**Source:** tailwindcss MIT `main@90f8ff41c8e2a4d17bc76921e23e9d672123da76`; Codebase Memory `tailwindcss`. **Question:** Where should a port cache parsed candidates, compiled ASTs, and negative results so that `@apply`, IntelliSense, and the main build all share one consistent view?

## buildDesignSystem caches
**Path/Symbol:** `packages/tailwindcss/src/design-system.ts:70-251` (`buildDesignSystem`), `packages/tailwindcss/src/utils/default-map.ts` (`DefaultMap`).
**Signature:** `buildDesignSystem(theme: Theme, utilitiesSrc?: SourceLocation): DesignSystem`.
**Data Shape:** `DesignSystem` = `{ theme, utilities, variants, invalidCandidates: Set<string>, important: boolean, ...closures }`; caches: `parsedVariants: DefaultMap<string, Variant|null>`, `parsedCandidates: DefaultMap<string, Readonly<Candidate>[]>`, `compiledAstNodes: DefaultMap<flags, DefaultMap<Candidate, rules>>`.

### Decisive source
```ts
let compiledAstNodes = new DefaultMap<number>((flags) => {
  return new DefaultMap<Candidate>((candidate) => {
    let ast = compileAstNodes(candidate, designSystem, flags)
    try {
      let nodes = ast.map((value) => value.node)
      // Arbitrary values can contain function calls so we need evaluate any
      // functions we find there that weren't in the source CSS.
      substituteFunctions(nodes, designSystem)
      // JS plugins might contain an `@variant` inside a generated utility
      substituteAtVariant(nodes, designSystem)
    } catch (err) {
      // If substitution fails then the candidate likely contains a call to
      // `theme()` that is invalid ...
      return []
    }
    return ast
  })
})
```

**Flow:** parse failures and compile misses are cached as *empty arrays*, not re-thrown; `compileCandidates` additionally records raw strings that produced nothing into `designSystem.invalidCandidates` (via the caller's `onInvalidCandidate`) so later builds skip them before parsing (`compile.ts:28-31`). The compiled cache is keyed by `CompileAstFlags` first (`None | RespectImportant`) because `@apply` compiles with important disabled while normal utilities respect the design system's `important` flag.
**Invariant:** Cache entries are immutable-by-convention — callers must never mutate returned nodes if they want reuse; source locations are back-filled with `node.src ??= utilitiesSrc` (nullish, so cached nodes keep their original assignment) only under full rebuild. Fail-soft substitution means an invalid `theme()` inside arbitrary values yields "no CSS" rather than crashing the build — but the empty result is also what gets cached.
**Probe:** `packages/tailwindcss/src/index.test.ts:557` "@apply does not cache important state" (flags-keyed caching observable), :603/:617 (@apply errors for unknown utility/variant), :3994 ("ignores invalid inline candidates"). Direct test runner: vitest at repo root (`vitest.config.ts`); not executed this pass — see verification note.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "tailwindcss", query: "buildDesignSystem DefaultMap parsedCandidates compiledAstNodes invalidCandidates", filePattern: "packages/tailwindcss/src/*", limit: 10, fields: ["lines"] });
```
Observed hits: `design-system.buildDesignSystem … design-system.ts 70-251`, plus the three `DefaultMap` members in `utils/default-map.ts`.

## Verdict
Adopt the two-level flags→candidate compile cache, parse-result memoization, and the negative-result Set fed from build callbacks. Adapt cache keys to your flag vocabulary (e.g. per-`@apply` context). Omit the `storage: Record<symbol, unknown>` escape hatch unless you have cross-plugin consumers needing namespaced scratch space.

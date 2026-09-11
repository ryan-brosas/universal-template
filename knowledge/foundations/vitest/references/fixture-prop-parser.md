<!-- capsule-v2 -->
# Fixture destructuring parser — how are a fixture function's dependencies extracted from its SOURCE TEXT, and which compiler-output shapes must the regex survive?

**Source:** Vitest (`vitest-dev/vitest`, MIT, `main@cf9176bf`). **Question:** How does `({ a, b }) => {}` become `{a, b}` at runtime without a real AST parse, and what error paths keep silent mis-resolution impossible?

## getUsedProps string parser
**Path/Symbol:** `packages/vitest/src/runtime/runner/fixture.ts:getUsedProps` (:637–702) with `splitByComma` (:704–728), memo symbols `kPropNamesSymbol/kPropsSymbol` (:612–630).
**Signature:** `function getUsedProps(fn: Function, { sourceError?, suiteHook? }?): Set<string>`; `splitByComma(s: string): string[]`.
**Data Shape:** result cached on the function itself (`kPropNamesSymbol`). Optional pre-annotation via `kPropsSymbol` (`{ index, original }`) for wrapped functions (e.g. each-ified or hook-wrapped fixtures where the fixture arg is not param 0). Errors: `FixtureParseError` (non-destructuring first arg, rest element) and `FixtureAccessError` (suite hook referencing fixtures it cannot receive).

### Decisive source
```ts
let fnString = filterOutComments(implementation.toString())   // strip comments FIRST

// esbuild --supported:async-await=false lowers to __async(this, null, function* ...)
// (also 'arguments' and [_0,_1] tuple forms) — split past the wrapper before parsing params
if (/__async\((?:this|null), (?:null|arguments|\[[_0-9, ]*\]), function\*/.test(fnString)) {
  fnString = fnString.split(/__async\((?:this|null),/)[1]
}
const match = fnString.match(/[^(]*\(([^)]*)/)
...
if (!(fixturesArgument[0] === '{' && fixturesArgument.endsWith('}'))) {
  throw new FixtureParseError(
    `The ${ordinalArgument} argument inside a fixture must use object destructuring pattern, e.g. ({ task } => {}). Instead, received "${fixturesArgument}".`)
}
const _first = fixturesArgument.slice(1, -1).replace(/\s/g, '')
const props = splitByComma(_first).map(prop => prop.replace(/:.*|=.*/g, ''))  // drop defaults/aliases
const last = props.at(-1)
if (last && last.startsWith('...')) {
  throw new FixtureParseError(`Rest parameters are not supported in fixtures, received "${last}".`)
}

// comma splitter is bracket-aware — commas inside nested {} / [] don't split
splitByComma: stack.push on '{'/'[', pop on matching close, split only when stack empty
```

**Flow:** fixture registration/resolution calls `getUsedProps(fn)` → memo hit returns instantly → else stringify, de-comment, unwrap possible `__async` lowering → regex out the first (or `index`-th) parameter → REQUIRE object-destructuring shape → strip whitespace, split bracket-aware, drop `alias:`/`=default` suffixes → reject `...rest` → memoize on the function. The same parser doubles as the suite-hook validator: hooks run WITHOUT context, so any detected props raise `FixtureAccessError` telling the user to call `test.beforeAll(...)` instead of bare `beforeAll(...)`.
**Invariant:** this is intentionally a STRING parser with loud failures, not an AST — porters who "upgrade" it to a full parse lose the exact error messages users depend on, and porters who skip the `__async` unwrap break every consumer transpiled with esbuild's lowered async. Comments between destructured props MUST be stripped before splitting (`filterOutComments`) — a `/* */` containing a comma would otherwise corrupt the prop list. Rest-element rejection is deliberate: deps must be statically enumerable.
**Probe:** `test/unit/test/fixture-comments-between-destructure.test.ts` (comment-stripping), `test/unit/test/fixture-initialization.test.ts` + `fixture-options.test.ts` (parse-driven resolution), `test/e2e/test/fixture-no-async.test.ts`; the source comment block itself carries the esbuild repro link (:649–652).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "vitest", query: "getUsedProps", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the destructure-string dependency extraction WITH its validation errors and lowering-unwrap for any convention-over-config DI surface. Adapt ordinal messages/symbol names. Omit the multi-arg `index` support if your host never wraps fixture functions.

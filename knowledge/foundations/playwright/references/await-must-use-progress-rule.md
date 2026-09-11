<!-- capsule-v2 -->
# await-must-use-progress rule — how does a repo make "every awaited call is cancellable" enforceable at CI time instead of by review folklore?

**Source:** playwright Apache-2.0 `main@d4e1023f6c03a8dced50eb3db88c2217e7c1a86a`; Codebase Memory `playwright`. **Question:** If cancellation only works when code routes awaits through `progress`, how do you stop contributors from accidentally writing an uncancellable `await someAsyncOp(...)` inside a cancellable API method?

## Type-aware ESLint rule over a Progress-parameter function stack
**Path/Symbol:** `utils/eslint-plugin-progress/index.js` (`hasProgressParam` 26-41, `isProgressRace` 46-55, `unwrapPromiseChain` 60-68, `passesProgressAsFirstArg` 74-86, `isInsideProgressRace` 103-114, rule body 116-195).
**Signature:** rule `await-must-use-progress`, no options; message: "Awaited async call must either pass `progress` as first argument or be wrapped in `progress.race()`. See packages/playwright-core/src/server/progress.ts."
**Data Shape:** input = AST of any function whose parameter is literally named `progress` AND whose declared type resolves (via TS type checker) to symbol/alias name `Progress` or stringifies to `'Progress'`.

### Decisive source
```ts
// Check await expressions in progress functions.
'AwaitExpression'(node) {
    if (!isInProgressFunction())
      return;
    const awaited = node.argument;
    // await progress.anything(...) is always fine — calls on the progress object itself.
    if (awaited.type === 'CallExpression' && ... object.name === 'progress') return;
    // await someCall(progress, ...) is fine.
    if (passesProgressAsFirstArg(awaited, services)) return;
    // Promise.all/race/allSettled/any are aggregation helpers, not async operations themselves.
    if (awaited.type === 'CallExpression' && ... ['all','race','allSettled','any'].includes(...)) return;
    // Check if this await is inside a progress.race() call higher up.
    if (isInsideProgressRace(node)) return;
    // Only flag async calls (calls that return Promise).
    if (awaited.type === 'CallExpression' && isAsyncCall(awaited, services))
      context.report({ node: awaited, messageId: 'missingProgress' });
}
```

**Flow:** the visitor keeps a stack of booleans pushed/popped on every function enter/exit, so nested callbacks inherit (or lose) "this is a Progress function" context correctly. For each AwaitExpression inside one, four escape hatches are checked in order — progress-object calls, progress-as-first-arg through `.then/.catch/.finally` chains (unwrapped to the root call and TYPE-CHECKED, so argument position matters), Promise aggregate helpers, and lexical enclosure in a `progress.race(...)`. Everything else that statically looks like a Promise (type has a `then` property) is reported at the call site.
**Invariant:** the rule is advisory-proof only because it is type-aware — a param named `progress` typed as anything else does NOT trigger it, and a Progress-typed value passed as a NON-first argument still fails; `isInsideProgressRace` deliberately stops climbing at function boundaries, so wrapping only YOUR await (not some helper's internals) satisfies it. This pairs with the runtime contract in `progress-controller-server`: raw `Promise.race` bypasses `_forceAbortPromise`, and this lint is what makes bypassing it a build failure.
**Probe:** repository-owned enforcement surface: the rule ships in `utils/eslint-plugin-progress/index.js` and is wired into the repo lint config; NO dedicated unit test file exists next to the plugin (verified by exact directory listing — only index.js). Execution BLOCKED standing in this lane (read-only checkout, no node_modules); deterministic evidence = byte-exact read of index.js:116-195 at pin HEAD plus the live graph nodes for `isProgressRace`/`isInsideProgressRace`/`passesProgressAsFirstArg`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "playwright", query: "progress controller deadline timeout race", limit: 25, fields: ["signature", "lines", "docstring"] });
```
(executed live → surfaced all seven plugin functions ranked alongside their runtime counterparts, e.g. `utils/eslint-plugin-progress.isProgressRace index.js 46-55`.)

## Verdict
Adopt the pattern of encoding your cancellation discipline as a type-aware lint rule with an explicit escape-hatch ordering; adapt the type-checking mechanism (uses @typescript-eslint parser services) and the exact escape hatches to your kernel's API names. Omit the specific `Promise.all/race/allSettled/any` exemption unless your aggregates are likewise pure combinators. Caveat recorded: no upstream test for the rule itself; treat its behavior as pinned by source inspection at this commit.

<!-- capsule-v2 -->
# CPA try-finally parallel lanes — how does one statement double your lane count, split heads in half, and route returns through finally?

**Source:** ESLint MIT `main@dc1e7a8416937edefe04cf836ee202a6fc03bedd`; Codebase Memory project `eslint`. **Question:** How do you model try/catch/finally so that `return` inside `try` provably passes through `finally` before leaving?

## TryContext machinery
**Path/Symbol:** `lib/linter/code-path-analysis/code-path-state.js:TryContext` (:541–602), `pushTryContext/popTryContext` (:1568–1647), `makeCatchBlock` (:1653–1675), `makeFinallyBlock` (:1685–1755), `makeYield` (:1762–1772), `makeFirstThrowablePathInTryOrCatchBlock` (:1780–1802), context finders `getReturnContext/getThrowContext` (:682–717).
**Signature:** `pushTryContext(hasFinalizer)`; TryContext holds `position:"try"|"catch"|"finally"`, `returnedForkContext` (only when hasFinalizer), `thrownForkContext`, `lastOfTryIsReachable/lastOfCatchIsReachable`.
**Data Shape:** with a finalizer the fork-context `count` doubles (see cpa-fork-context); every row is [normalLane…, leavingLane…] and `popTryContext` splits the head at `length/2`.

### Decisive source
```js
// popTryContext — only when a finally exists AND try/catch contained return/throw:
const normalSegments   = headSegments.slice(0, (headSegments.length / 2) | 0);
const leavingSegments  = headSegments.slice((headSegments.length / 2) | 0);
if (!originalReturnedForkContext.empty)
  getReturnContext(this).returnedForkContext.add(leavingSegments);   // leave-paths hop OUT
if (!originalThrownForkContext.empty)
  getThrowContext(this).thrownForkContext.add(leavingSegments);
this.forkContext.replaceHead(normalSegments);                        // normal path continues
if (!context.lastOfTryIsReachable && !context.lastOfCatchIsReachable)
  this.forkContext.makeUnreachable();                                // both dead ⇒ next dead
```

**Flow:** `return` (via `getReturnContext`) lands in the *innermost enclosing* try-with-finalizer's `returnedForkContext` — skipping finally-free trys; `throw` behaves likewise but only for position `"try"` or (`"catch"` ∧ hasFinalizer). Entering `finally` (`makeFinallyBlock`) synthesizes per-column leaving segments whose prevs = current head column + all returned + all thrown rows, then pushes a fork with `shouldForkLeavingPath=true`. Catch entry merges thrown paths plus a bypass from pre-try flow. `makeYield` treats a suspended yield as BOTH a return-like and throw-like exit (generator resumption may propagate either) then continues into a fresh segment.
**Invariant:** the half-split is only legal because finally doubled `count`; `lastOfTryIsReachable && !lastOfCatchIsReachable` style bookkeeping decides post-try reachability — if both blocks ended unreachable the continuation must be marked unreachable, not merely empty; first-throwable wiring fires ONCE per block (`!context.thrownForkContext.empty` re-entry guard).
**Probe:** `tests/lib/linter/code-path-analysis/code-path-analyzer.js` (:536–794 unreachable-event suites after throw/return incl. "inside of function and if statement"; :1021 fixtures sweep).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "eslint", query: "popTryContext makeFinallyBlock returnedForkContext makeFirstThrowablePathInTryOrCatchBlock", limit: 10, fields: ["signature", "name", "file"] });
await mcp.codebase_memory.get_code_snippet({ project: "eslint", qualified_name: "eslint.lib.linter.code-path-analysis.code-path-state.CodePathState.makeFinallyBlock" });
```

## Verdict
Adopt lane-doubling + half-split + innermost-with-finalizer routing for any language where cleanup blocks intercept abrupt exits; adapt the position state-machine to your try grammar; omit yield duality unless you model generators.

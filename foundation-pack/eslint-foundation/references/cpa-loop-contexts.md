<!-- capsule-v2 -->
# CPA loop-context family — how do five loop grammars share break/continue wiring with per-grammar continue destinations?

**Source:** ESLint MIT `main@dc1e7a8416937edefe04cf836ee202a6fc03bedd`; Codebase Memory project `eslint`. **Question:** How do you wire `break`/`continue` edges for while / do-while / for / for-in / for-of without five bespoke algorithms?

## LoopContexts + popLoopContext
**Path/Symbol:** `lib/linter/code-path-analysis/code-path-state.js:LoopContextBase` (:183–216) and subclasses (:221–475), `pushLoopContext/popLoopContext` (:1817–1963), per-phase `makeWhileTest/makeWhileBody/makeDoWhileBody/makeDoWhileTest/makeForTest/makeForUpdate/makeForBody/makeForInOfLeft/Right/Body` (:1970–2234), abrupt exits `makeBreak/makeContinue` (:2289–2343), edge synthesizer `makeLooped` (:759–814), helper `finalizeTestSegmentsOfFor` (:826–848).
**Signature:** each loop context records phase segment arrays (`endOfInitSegments/testSegments/endOfTestSegments/updateSegments/endOfUpdateSegments`, for-in/of: `prevSegments/leftSegments/endOfLeftSegments`) plus `continueDestSegments`; every loop also pushes a *breakable* BreakContext.
**Data Shape:** `makeLooped(from[], to[])` pairs by index after flattening unused segments; pushes reachable edges only when both ends reachable, always updates the `all*` views, and marks `markPrevSegmentAsLooped` when a destination gains its ≥2nd prev.

### Decisive source
```js
// continue target differs per grammar:
case "WhileStatement": case "ForStatement":
  makeLooped(this, forkContext.head, context.continueDestSegments); break; // → test/update
case "DoWhileStatement": /* true-fork loops back to entrySegments */       // → body top
case "ForInStatement": case "ForOfStatement":
  makeLooped(this, forkContext.head, context.leftSegments); break;         // → LEFT expr
// after the switch: no break ever seen ⇒ continuation is unreachable
if (brokenForkContext.empty) forkContext.replaceHead(forkContext.makeUnreachable(-1,-1));
else                         forkContext.replaceHead(brokenForkContext.makeNext(0,-1));
```

**Flow:** loops push (BreakContext breakable=true, optional ChoiceContext kind "loop", typed LoopContext). Phase hooks fire from `preprocess` keyed on which child position is being entered (`parent.test===node` ⇒ makeForTest…). For-loops re-target `continueDestSegments` mid-flight: test ⇒ update when an update expression exists (`makeForUpdate` uses `makeDisconnected` so the update segment doesn't yet link back). Constant tests (`while(true)`) are captured as literal booleans (`getBooleanValueIfSimpleConstant`) — `test !== true` routes the false-fork into `brokenForkContext` so code after an infinite loop stays unreachable unless a `break` exists. Labeled non-breakable statements push their own unbreakable BreakContext so labeled `break` can find them by name (`getBreakContext` walks `upper` matching label or `breakable`).
**Invariant:** `continue` inside for-in/of ALSO feeds that lane into `brokenForkContext` (:2331–2337 comment: "this affects a break also") because iteration advance doubles as loop exit; `while(true){}` without break must end in unreachable continuation — porters who skip constant-test capture emit false-reachable tails; `do-while` is the only loop whose continue destination can be deferred (`continueForkContext` drained at `makeDoWhileTest`).
**Probe:** `tests/lib/linter/code-path-analysis/code-path-analyzer.js:795–1010` (`onCodePathSegmentLoop` fired exactly once in while/do-while/for/for-in/for-of) + `tests/lib/linter/code-path-analysis/code-path.js` traverse fixtures (:199/:219/:248).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "eslint", query: "pushLoopContext popLoopContext makeForUpdate makeContinue brokenForkContext", limit: 10, fields: ["signature", "name", "file"] });
await mcp.codebase_memory.get_code_snippet({ project: "eslint", qualified_name: "eslint.lib.linter.code-path-analysis.code-path-state.CodePathState.popLoopContext" });
```

## Verdict
Adopt the phase-hook decomposition + shared makeLooped primitive + per-grammar continueDest indirection; adapt loop grammar coverage to your language; omit the constant-test reachability propagation if your host never folds constants (record it!).

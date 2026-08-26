<!-- capsule-v2 -->
# CPA switch default-rewiring — how do you make `default` fall through correctly when it is NOT the last case?

**Source:** ESLint MIT `main@dc1e7a8416937edefe04cf836ee202a6fc03bedd`; Codebase Memory project `eslint`. **Question:** How do you keep the segment graph faithful to runtime order when source order (case A, default, case B) differs from execution order?

## SwitchContext + popSwitchContext
**Path/Symbol:** `lib/linter/code-path-analysis/code-path-state.js:SwitchContext` (:485–536), `pushSwitchContext/popSwitchContext` (:1399–1486), `makeSwitchCaseBody` (:1494–1556), edge surgery helpers `disconnectSegments` (:739–749), `makeLooped` reuse, analyzer-side fork points `code-path-analyzer.js` (:312–314 case-fork on entry, :505–514 skip-fork for cases after the first, :576–588 empty-consequent handling).
**Signature:** `pushSwitchContext(hasCase, label)` (also pushes breakable BreakContext); SwitchContext tracks `defaultSegments/defaultBodySegments/foundEmptyDefault/lastIsDefault/forkCount`.
**Data Shape:** each `case` body start forks once (`forkCount` = cases + present default); a `default` with empty consequent only records `foundEmptyDefault=true`, deferring body resolution to the next non-empty case.

### Decisive source
```js
if (!context.lastIsDefault) {
  if (context.defaultBodySegments) {
    // default sits mid-switch: erase its source-order link...
    disconnectSegments(context.defaultSegments, context.defaultBodySegments);
    // ...and connect the LAST non-default case's fall-through into it instead
    makeLooped(this, lastCaseSegments, context.defaultBodySegments);
  } else {
    // no default at all ⇒ treat last case as if it ended in `break`
    brokenForkContext.add(lastCaseSegments);
  }
}
// climb out of every per-case fork before replacing the head:
for (let i = 0; i < context.forkCount; ++i) this.forkContext = this.forkContext.upper;
this.forkContext.replaceHead(brokenForkContext.makeNext(0, -1));
```

**Flow:** entering each SwitchCase after the first forks a fresh path from the discriminant chain (`parent.discriminant !== node && parent.cases[0] !== node`); an empty consequent gets its body-transition replayed at exit (`makeSwitchCaseBody(true,…)` at `processCodePathToExit`) so empty cases still join the fall-through chain. An early *empty* default is re-homed: the first non-empty case after it becomes the effective default body (`foundEmptyDefault=false; defaultBodySegments=forkContext.head`).
**Invariant:** never emit default's edges in source order — disconnect-then-reloop is what makes "switch falls to matching case, else to default wherever it sits" true in the graph; `forkCount` must unwind ALL per-case fork contexts or subsequent statements inherit a phantom stack.
**Probe:** `tests/lib/linter/code-path-analysis/code-path.js` switch traverse fixture (:166) + `tests/lib/linter/linter.js` code-path consumer rules.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "eslint", query: "popSwitchContext disconnectSegments defaultBodySegments foundEmptyDefault", limit: 10, fields: ["signature", "name", "file"] });
await mcp.codebase_memory.get_code_snippet({ project: "eslint", qualified_name: "eslint.lib.linter.code-path-analysis.code-path-state.CodePathState.popSwitchContext" });
```

## Verdict
Adopt disconnect+reloop rewiring and the empty-default re-homing rule; adapt to your switch grammar (e.g. pattern-match arm ordering); omit label plumbing if your language has no labeled break.

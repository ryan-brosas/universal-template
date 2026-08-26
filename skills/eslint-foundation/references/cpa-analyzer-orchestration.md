<!-- capsule-v2 -->
# CPA analyzer orchestration — how does one EventGenerator wrapper turn an AST walk into code-path events without changing the wrapped visitor?

**Source:** ESLint MIT `main@dc1e7a8416937edefe04cf836ee202a6fc03bedd`; Codebase Memory project `eslint`. **Question:** How do you interleave code-path bookkeeping into an existing AST traversal so rules receive `onCodePath*` events in exactly the right order around their node callbacks?

## CodePathAnalyzer
**Path/Symbol:** `lib/linter/code-path-analysis/code-path-analyzer.js:CodePathAnalyzer` (:747–829) + module helpers `forwardCurrentToHead` (:179–221), `preprocess` (:258–382), `processCodePathToEnter` (:390–537), `processCodePathToExit` (:545–663), `postprocess` (:671–737).
**Signature:** `new CodePathAnalyzer(eventGenerator)`; `enterNode(node)`; `leaveNode(node)`; `onLooped(fromSegment, toSegment)`. The analyzer implements the same EventGenerator interface it wraps.
**Data Shape:** per-CodePath mutable `CodePathState` (reached via `CodePath.getState`); `state.currentSegments` vs `state.headSegments` are two parallel arrays indexed by fork depth; analyzer holds one `IdGenerator("s")` for path ids and `currentNode` for loop-event attribution.

### Decisive source
```js
// enterNode: position-based forks FIRST (parent known), then type-based state pushes,
// then delegate to the wrapped generator, so rule enter callbacks see post-fork state.
if (node.parent) { preprocess(this, node); }        // makeIfConsequent / makeLogicalRight / ...
processCodePathToEnter(this, node);                 // startCodePath / pushChoiceContext / pushLoopContext
this.original.enterNode(node);
// leaveNode mirrors it: type-based pops run BEFORE the wrapped leaveNode,
// and path-finalization (postprocess/endCodePath) runs AFTER it.
processCodePathToExit(this, node);
this.original.leaveNode(node);
postprocess(this, node);
```

**Flow:** enter = preprocess(parent-position forks) → toEnter(type pushes + possible `startCodePath`) → forward current→head segments → wrapped enter. Exit = toExit(context pops + abrupt-completion wiring, may set `dontForward`) → wrapped leave → postprocess (`endCodePath` for Program/Function*/StaticBlock/PropertyDefinition value). New CodePath starts on Program/function-ish nodes/class field initializers/class static blocks (`origin`: "program"|"function"|"class-field-initializer"|"class-static-block"); a PropertyDefinition value starts its path *and falls through* to also start the arrow-function path nested inside (`a = () => {}` opens two paths), closed in reverse order at exit.
**Invariant:** the wrapped visitor's event stream is never reordered — every emitted segment event happens strictly before the corresponding rule callback on enter, and after it on leave; `forwardCurrentToHead` fires end-events for diverged current segments before start-events for head segments (git-branch analogy: track current vs head kept separate to avoid emitting useless segments); unreachable segments emit `onUnreachableCodePathSegment{Start,End}` instead of the reachable variants, keyed off `segment.reachable`, and only reachable loops fire `onCodePathSegmentLoop`.
**Probe:** `tests/lib/linter/code-path-analysis/code-path-analyzer.js` (:255–794 event-order suites; :393 initial-segment start; :536/:614 unreachable events after throw/return).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "eslint", query: "CodePathAnalyzer enterNode preprocess processCodePathToExit", limit: 10, fields: ["signature", "name", "file"] });
await mcp.codebase_memory.trace_path({ project: "eslint", function_name: "eslint.lib.linter.code-path-analysis.code-path-analyzer.CodePathAnalyzer.enterNode", direction: "outbound", depth: 1 });
```

## Verdict
Adopt the wrapper-decorator pattern and the strict enter(pre)/type-push/delegate ordering; adapt the node-type switch to your AST dialect; omit ESLint's debug dot-dump hooks unless you need graph visualization parity.

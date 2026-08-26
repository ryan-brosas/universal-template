<!-- capsule-v2 -->
# Post-collection mode interpretation — how do only/skip/todo/name/location/tag filters rewrite a collected task tree without re-running collection?

**Source:** Vitest (`vitest-dev/vitest`, MIT, `main@c3ba16b35847`); Codebase Memory `vitest`. **Question:** After tests are collected, what single pass turns `.only`, CLI name patterns, line locations, ids, and tags into final run/skip/todo modes — and why does unauthorized `.only` not crash the run?

## Recursive `interpretTaskModes` traversal
**Path/Symbol:** `packages/vitest/src/utils/tasks.ts:interpretTaskModes` (231–352) + private `checkAllowOnly` (375–392), `skipAllTasks`/`todoAllTasks` (354–373). Collection-side inputs computed in `runtime/runner/suite.ts:createSuiteCollector.collect` (`containsOnly`/`containsTest` bubble-up). Callers: `node/core.ts` Vitest.collect/start, `runtime/runner/collect.ts:collectTests`, `runtime/runner/run.ts:startTests/publicCollect`.
**Signature:** `interpretTaskModes(file: Suite, namePattern?: string|RegExp, testLocations?: number[], testIds?: string[], testTagsFilter?: ((tags:string[])=>boolean), onlyMode?: boolean, parentIsOnly?: boolean, allowOnly?: boolean): void` — mutates the tree in place.
**Data Shape:** consumes per-task `mode` ('run'|'skip'|'todo'|'only'|'queued'), suite-level `containsOnly`/`containsTest` flags recorded during collection; writes final `mode`; may attach `file.result.errors` for unmatched locations.

### Decisive source
```ts
const suiteIsOnly = parentIsOnly || suite.mode === 'only'
const hasSomeTasksOnly = !!(onlyMode && suite.containsOnly)
suite.tasks.forEach((t) => {
  const includeTask = hasSomeTasksOnly
    ? (t.mode === 'only' || (t.type === 'suite' && !!t.containsOnly))
    : (suiteIsOnly || t.mode === 'only')
  if (onlyMode) {
    if (t.type === 'suite' && (includeTask || t.containsOnly)) {
      if (t.mode === 'only') { checkAllowOnly(t, allowOnly); t.mode = 'run' }
    }
    else if (t.mode === 'run' && !includeTask) { t.mode = 'skip' }
    else if (t.mode === 'only') { checkAllowOnly(t, allowOnly); t.mode = 'run' }
  }
  ...
  else if (t.type === 'suite') {
    if (t.mode === 'skip') { skipAllTasks(t) }
    else if (t.mode === 'todo') { todoAllTasks(t) }
    else { traverseSuite(t, includeTask, hasLocationMatch) }
  }
})
// empty-after-filter suites collapse:
if ((suite.mode === 'run' || suite.mode === 'queued')
    && suite.tasks.length
    && suite.tasks.every(i => i.mode !== 'run' && i.mode !== 'queued')) suite.mode = 'skip'

function checkAllowOnly(task: TaskBase, allowOnly?: boolean) {
  if (allowOnly) return
  const error = new Error('[Vitest] Unexpected .only modifier. Remove it or pass --allowOnly argument to bypass this error')
  task.result = { state: 'fail', errors: [{ name: error.name, message: error.message, stack: error.stack }] }
}
```

**Flow:** one DFS from the file node → only-resolution first (`hasSomeTasksOnly` narrows a mixed suite to its `.only` members; an `.only` SUITE keeps all children via `suiteIsOnly`) → then filter ladder flips non-matching tests to `'skip'`: location lines (parent match includes whole subtree; unmatched requested lines are collected), full-name regex, task-id set, tag predicate → skipped/todo suites force-cascade their subtree (`skipAllTasks`/`todoAllTasks` only touch still-`run|queued` tasks) → suites whose every child lost `run` collapse to `'skip'` → finally unmatched requested locations push "No test found in `<file>` in line(s) X" onto `file.result.errors`.
**Invariant:** (1) collection happens once; filtering is pure tree rewriting — no test module is re-imported or re-parsed to change selection; (2) `.only` without `allowOnly` never throws out of the walk: the offending task is given a failing result so reporters surface it while the run completes; (3) mode precedence survives any nesting order because `parentIsOnly`/`parentMatchedWithLocation` thread through recursion; (4) a suite with ZERO tasks never collapses to skip (the `tasks.length` guard).

**Probe:** `test/unit/test/modes.test.ts` — self-referential battery: nested `describe('test.only in nested described')` pins that a sibling test is skipped while the focused one runs under allowOnly; `it.concurrent.skip`/`it.skip.concurrent` order-insensitivity and `concurrent.todo` variants. `test/e2e/test/static-collect.test.ts:1644` builds collectors with `allowOnly:true`; `test/e2e/test/pre-parse.test.ts:334` same for AST collection. Caveat: no unit file imports `interpretTaskModes` directly — behavior is pinned end-to-end.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.trace_path({ project: "vitest", function_name: "vitest.packages.vitest.src.utils.tasks.interpretTaskModes", direction: "inbound", depth: 2 });
// observed callers_total 7: Vitest.collect/start/experimental_parseSpecification(s),
// runtime collectTests, publicCollect, startTests.
```

## Verdict
Adopt the single-pass recursive interpreter with contains-bubbling and fail-the-task (not fail-the-run) allowOnly enforcement. Adapt the filter vocabulary (locations need `includeTaskLocation` capture at collection time) to your host's selectors. Omit vitest's AST/static collectors; this capsule governs the runtime-collected shape they share.

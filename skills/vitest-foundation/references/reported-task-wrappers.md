<!-- capsule-v2 -->
# Reported-task wrapper layer — how does the public reporter API expose stable TestCase/TestSuite/TestModule objects over mutable runner tasks without leaking identity bugs?

**Source:** Vitest (`vitest-dev/vitest`, MIT, `main@cf9176bf`). **Question:** How are public task entities registered, looked up, and state-mapped so a porter's reporter reads consistent objects across a whole run?

## register + WeakMap + getSuiteState
**Path/Symbol:** `packages/vitest/src/node/reporters/reported-tasks.ts` — `ReportedTaskImplementation.register` (:81–85), `storeTask` (:765–771), `getReportedTask` (:773–784), `TestCase.result()` (:159–199), `getSuiteState` (:786–802).
**Signature:** `static register(task: RunnerTask, project: TestProject): TestCase | TestSuite | TestModule`; `state.getReportedEntity(task): entity | undefined`.
**Data Shape:** `StateManager.reportedTasksMap: WeakMap<RunnerTask, ReportedEntity>` (state.ts:25) keyed by the RUNNER task object; wrappers hold `readonly task`, `project`, `id = task.id`, `location`. Lookup failure throws `Task instance was not found for <type> "<name>"`.

### Decisive source
```ts
static register(task: RunnerTask, project: TestProject) {
  const state = new this(task, project) as TestCase | TestSuite | TestModule
  storeTask(project, task, state)      // project.vitest.state.reportedTasksMap.set(runnerTask, reportedTask)
  return state
}
function getReportedTask(project: TestProject, runnerTask: RunnerTask) {
  const reportedTask = project.vitest.state.getReportedEntity(runnerTask)
  if (!reportedTask) {
    throw new Error(`Task instance was not found for ${runnerTask.type} "${runnerTask.name}"`)
  }
  return reportedTask
}

// suite state mapping — mode/result merge with explicit unknown-state throw
function getSuiteState(task: RunnerTestSuite | RunnerTestFile): TestSuiteState {
  const mode = task.mode
  const state = task.result?.state
  if (mode === 'skip' || mode === 'todo' || state === 'skip' || state === 'todo') return 'skipped'
  if (state == null || state === 'run' || state === 'only') return 'pending'
  if (state === 'fail') return 'failed'
  if (state === 'pass') return 'passed'
  throw new Error(`Unknown suite state: ${state}`)
}

// test result mapping — result.state wins over mode; missing result + skip/todo mode => skipped
if (!result && (mode === 'skip' || mode === 'todo')) return { state: 'skipped', note: undefined, errors: undefined }
if (!result || result.state === 'run' || result.state === 'queued') return { state: 'pending', errors: undefined }
```

**Flow:** runner creates tasks → node-side `StateManager.collectFiles/updateId/cancelFiles/clearFiles` call `register()` per task (`trace_path`: callers `collectFiles`, `updateId`, `cancelFiles`, `clearFiles`, plus `experimental_parseSpecification(s)`) → wrappers cross-link via `getReportedTask` (child→parent, test→module) → reporters read `.result()/.state()/.diagnostic()` which map internal states to the public vocabulary.
**Invariant:** ONE wrapper instance per runner task for the whole run — the WeakMap is the identity table; creating wrappers on demand would break `===` comparisons in user reporters and re-run `fullName` memoization. State mapping precedence is deliberate: `result.state` beats `task.mode` for finished tests, but a MISSING result falls back to mode (skip/todo ⇒ skipped, else pending). Suites expose only the 4-state vocabulary; modules add `'queued'` BEFORE delegating to the suite mapper. `ok()` treats unfinished/skipped as success (`!result || result.state !== 'fail'`); flaky = `retryCount > 0 && state === 'pass'`.
**Probe:** `test/e2e/test/reported-tasks.test.ts` pins fullName composition (`'a group > a nested group > runs a test in a nested group'` :302), module+test diagnostics (:96/:134/:308), and repeated/flaky diagnostics (:272/:283); `test/e2e/fixtures/reporters/` exercises the entities from every built-in reporter.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "vitest", query: "ReportedTaskImplementation.register", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the WeakMap identity table + strict state-mapping functions for any reporter-facing API over live run state. Adapt the public vocabulary names to your host. Omit `experimental_getRunnerTask` escape hatch unless your host needs raw-task interop.

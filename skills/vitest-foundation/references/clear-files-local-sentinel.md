<!-- capsule-v2 -->
# Clear-files local sentinel — how does watch mode keep console logs attachable for a file that was invalidated before its workers re-registered it?

**Source:** Vitest (`vitest-dev/vitest`, MIT, `main@cf9176bf`); Codebase Memory `vitest`. **Question:** What must remain in the state maps after clearing a file's tasks so a re-run can still attribute logs and results?

## Local placeholder registration
**Path/Symbol:** `packages/vitest/src/node/state.ts:StateManager.clearFiles` (:170–199), `updateId` (:201–222), `getSuiteFilepath` twin at `runtime/moduleRunner/bareModuleMocker.ts:getMockerRegistry` (:70–76).
**Signature:** `clearFiles(project: TestProject, paths?: string[]): void`; `updateId(task: Task, project: TestProject): void`.
**Data Shape:** creates `createFileTask(path, root, name)` with `local = true`, registers it as TestModule, seeds `idMap` and `filesMap[path]`. The filesMap entry keeps OTHER projects' real File tasks alongside the local one.

### Decisive source
```ts
const fileTask = createFileTask(path, project.config.root, project.config.name)
fileTask.local = true                      // sentinel: not a real run's file
TestModule.register(fileTask, project)     // wrapper exists BEFORE any result arrives
this.idMap.set(fileTask.id, fileTask)
if (!files) { this.filesMap.set(path, [fileTask]); return }
const filtered = files.filter(file => file.projectName !== project.config.name)
// always keep a File task, so we can associate logs with it
this.filesMap.set(path, filtered.length ? [...filtered, fileTask] : [fileTask])
```

**Flow:** browser/watch pool invalidates files (`pools/browser.ts:106`) → clearFiles removes that PROJECT's File entries but always leaves one `local: true` sentinel → worker later collects/updates via `collectFiles` → `updateId` short-circuits when `idMap.get(task.id) === task` (already current), else registers the reported-entity wrapper recursively over suite children.
**Invariant:** a filepath key must never become EMPTY in filesMap — logs arriving between clear and recollect need an owning task (`updateUserLog` resolves through idMap). The sentinel is per-project-filtered: other projects' live entries survive untouched. `getFiles()` filters `file.local` out of reporting, so sentinels are invisible to reporters but present to log routing. updateId's identity short-circuit prevents wrapper re-registration (which would break WeakMap identity).
**Probe:** `test/e2e/test/repeats.test.ts:16` exercises the collect→getReportedEntity path that sentinels hand off to; `test/e2e/fixtures/reporters/` exercises reporting across re-collected modules. Coverage caveat: no direct test asserts `local` filtering; probe is indirect e2e.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "vitest", query: "clearFiles createFileTask local updateUserLog updateId", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the never-empty-key rule with a flagged placeholder task whenever invalidation can race log arrival. Adapt the flag name/filter sites to your reporter surface. Omit the multi-project tuple logic if your host has single-project runs (then a plain placeholder suffices).

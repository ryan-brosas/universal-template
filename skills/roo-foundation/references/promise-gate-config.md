<!-- capsule-v2 -->
# Promise-gate late config — how do you serve synchronous consumers when configuration arrives asynchronously?

**Source:** Roo-Code Apache-2.0 `main@b867ec9145750d0ae1ff7f02d35406e9bf2a0b16`; Codebase Memory `Roo-Code`. **Question:** A porter's Task object needs `taskMode` at construction but provider state loads async — how does roo make the race impossible?

## Readiness promise published beside every late field
**Path/Symbol:** `src/core/task/Task.ts` (4,619L; `_taskMode` + `taskModeReady` promise gate, twin `taskApiConfigReady` for provider profiles; fields ~:293-330, init ~:419-513).
**Signature:** private `_taskMode` field paired with `taskModeReady: Promise<void>`; consumers `await task.taskModeReady` before touching `task.taskMode`.
**Data Shape:** New tasks initialize mode from provider state ASYNC (falling back to `defaultModeSlug`); history-resumed tasks initialize SYNCHRONOUSLY; the field doc states the contract outright: access only after the readiness promise resolves.

### Decisive source
```ts
// Field doc contract (Task.ts):
// new_task: initialize mode from provider state ASYNC, fallback defaultModeSlug;
// history items: initialize synchronously.
// Access only after taskModeReady resolves.
this.consecutiveMistakeLimit = consecutiveMistakeLimit ?? DEFAULT_CONSECUTIVE_MISTAKE_LIMIT;
this.toolRepetitionDetector = new ToolRepetitionDetector(this.consecutiveMistakeLimit);
```

**Flow:** constructor starts the async load and stores its promise → any consumer needing the value awaits the gate first → once resolved, access is plain and synchronous. The same pattern gates API-config selection (`taskApiConfigReady`).
**Invariant:** Never expose a half-initialized config field: publish a readiness promise NEXT TO each late field so races become impossible by construction rather than by discipline. Sync-available paths (history resume) still resolve the gate so callers need no dual code path.
**Probe:** No dedicated spec isolates the gate at this HEAD — coverage caveat; deterministic probes: field-doc contract verbatim in `src/core/task/Task.ts`, gate consumption via `grep -n "taskModeReady" src/core/task/Task.ts`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Roo-Code", query: "taskModeReady promise gate Task", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the readiness-promise-next-to-field pattern wholesale — it is host-agnostic. Adapt naming to your config surface. Omit nothing. Coverage caveat noted above.

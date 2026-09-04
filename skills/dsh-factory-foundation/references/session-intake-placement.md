<!-- capsule-v2 -->
# Session intake — how does a blank chat composer become durable graph work without prompting the session?

**Source:** dsh-factory MIT `main@3405edc7`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-dsh-factory`. **Question:** How do I convert an existing live session into a draft task (or flow node) with placement semantics, without stealing or duplicating it?

## intakeSession
**Path/Symbol:** `packages/domain/src/index.ts` (`FactoryDomain.intakeSession`) (:289–438).
**Signature:** `async intakeSession(request: FactorySessionIntakeRequest): Promise<FactorySessionIntakeResult>`; placements `'parallel' | 'sequential' | 'finalizer'`.
**Data Shape:** requires a BLANK idle session (no `user/message` event ever); destinations `task | new-flow | flow`; returns `{ taskId, snapshot }`; task keeps `intakeSessionId` linking back.

### Decisive source
```ts
if (agent.status !== 'idle' || agent.session.events.some(event => event.type === 'user/message'))
    throw new Error(`Factory intake requires a blank idle Session: ${request.sessionId}`)
...
const ordinaryTasks = memberTasks.filter(candidate => !candidate.finalizer)
const dependedOn = new Set(ordinaryTasks.flatMap(candidate => candidate.dependencyIds))
const leaves = ordinaryTasks.filter(candidate => !dependedOn.has(candidate.id)).map(candidate => candidate.id)
task.dependencyIds = request.placement === 'parallel' ? [] : leaves
task.finalizer = request.placement === 'finalizer'
if (task.finalizer) task.finalizerPolicy = 'always'
else {
    delete task.finalizerPolicy
    for (const finalizer of memberTasks.filter(candidate => candidate.finalizer)) {
      if (finalizer.activeRunId !== undefined) throw new Error(`Factory finalizer ${finalizer.identifier} is already active`)
      finalizer.dependencyIds = [...new Set([...finalizer.dependencyIds, task.id])]
    }
}
```

**Flow:** validate blank+idle and destination/placement pairing → resolve workspace project from session cwd → find-or-create the intake task (rejects if a run already owns the session) → overwrite prompt/metadata/preset/model from the session header → route to destination: task→inbox-or-standard, new-flow→mirror-named standard flow, existing-flow→validated same-workspace non-terminal → apply PLACEMENT: parallel = no deps; sequential = depend on current LEAVES (computed over ordinary members); finalizer = become an always-finalizer, else every existing finalizer gains this task as a dependency → deriveFlows.
**Invariant:** Intake never sends a message into the adopted session — it only records work ABOUT it; leaf-computation makes "sequential" append after the current tail without touching interior edges; converting to finalizer flips the graph so cleanup runs last regardless of where the user dropped the card.
**Probe:** `packages/domain/tests/domain.spec.ts` "places New Session tasks as sequential, finalizer, or parallel nodes in an existing flow" + "creates one draft Emerging task from a blank Session without prompting or binding it". Deterministic from repo root: `grep -c "request.placement === 'parallel'" packages/domain/src/index.ts` = 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-dsh-factory", query: "FactorySessionIntakeRequest", limit: 5, fields: ["signature", "name", "file"] });
```
(CLI equivalent verified via sibling name-pattern queries on this project.)

## Verdict
Adopt blank-idle gating + leaf-based sequential placement + finalizer conversion. Adapt session-header field names. Omit UI composer mirroring.

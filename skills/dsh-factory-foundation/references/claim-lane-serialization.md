<!-- capsule-v2 -->
# Claim lane serialization — how does claiming respect both global concurrency and per-checkout exclusivity?

**Source:** dsh-factory MIT `main@3405edc7`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-dsh-factory`. **Question:** How do I atomically reserve work up to a concurrency cap while guaranteeing two tasks never write the same checkout at once?

## claimReadyTasks with lane-key occupation
**Path/Symbol:** `packages/domain/src/index.ts` (`FactoryDomain.claimReadyTasks`, `lanePath`) (:793–824, :1042–1049).
**Signature:** `async claimReadyTasks(limit: number): Promise<FactoryTaskClaim[]>`; `private lanePath(document, task, activePath?): string`.
**Data Shape:** runs carry `checkoutPath?`; ready tasks come from the protocol's priority-sorted `readyTasks(document)`; claims returned as cloned `{ task, project, run }`.

### Decisive source
```ts
const committed = await this.ctx.factoryStore.mutate(undefined, (document) => {
    const occupied = new Set<string>()
    let activeCount = 0
    for (const run of document.runs) {
      if (!['dispatching', 'running', 'waiting'].includes(run.status)) continue
      activeCount += 1
      const task = document.tasks.find(candidate => candidate.id === run.taskId)
      if (task !== undefined) occupied.add(this.lanePath(document, task, run.checkoutPath))
    }
    const available = Math.max(0, limit - activeCount)
    for (const task of readyTasks(document)) {
      if (claimed.length >= available) break
      const path = this.lanePath(document, task)
      if (occupied.has(path)) continue
      ...
```
with `lanePath`: active run → `` `path:${activePath}` ``; isolated → `` `isolated:${task.id}` ``; current → `` `path:${project.mainPath}` ``; reuse → predecessor's output checkout or main path.

**Flow:** inside ONE lease-guarded store transaction → collect active-run lane keys into `occupied` → `available = max(0, limit - activeCount)` → walk priority-ordered ready tasks, skip occupied lanes, `addRun` per claim → commit; callers receive claims resolved from the COMMITTED document. The scheduler's own in-memory `active` map adds a second idempotence layer (`start()` skips already-active task ids).
**Invariant:** Global concurrency is enforced against ALL live runs in the document (not just this process's), and per-lane exclusivity by serialized key — so two `current`-mode tasks on one workspace can never run simultaneously even when global capacity remains (direct test: "serializes current-checkout tasks even when global capacity remains").
**Probe:** `packages/domain/tests/domain.spec.ts` "claims explicit parallel roots, then unlocks their dependent node" and "serializes current-checkout tasks even when global capacity remains". Deterministic from repo root: `grep -c 'occupied.has(path)' packages/domain/src/index.ts` = 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-dsh-factory", query: "readyTasks", limit: 5, fields: ["signature", "name", "file"] });
```
(CLI equivalent verified live: name-exact Function node rank-1 in packages/protocol/src/graph.ts.)

## Verdict
Adopt lane-key occupation + capacity accounting inside one transaction. Adapt lane key vocabulary to host checkout strategy. Omit worktree provider specifics (host git tooling).

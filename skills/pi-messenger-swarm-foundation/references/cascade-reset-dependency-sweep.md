<!-- capsule-v2 -->
# Cascade reset dependency sweep — how does resetting a task invalidate everything that depended on it?

**Source:** pi-messenger-swarm MIT `main@6fe429a4b74ae276a621bb72910d7926fb6b3104`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-messenger-swarm`. **Question:** What exactly does `task reset --cascade` reset, and in what order?

## Only DONE dependents are reset, transitively, after the root
**Path/Symbol:** `swarm/task-store/commands.ts:resetTask` (:167-213).
**Signature:** `resetTask(cwd, sessionId, taskId, cascade = false): SwarmTask[]` — returns root + every reset dependent.
**Data Shape:** depends_on edges only; the sweep collects a Set of ids to reset BEFORE appending any events.

### Decisive source
```ts
if (cascade) {
  const allTasks = getAllTasks(cwd, sessionId);
  const doneIds = new Set(allTasks.filter((t) => t.status === 'done').map((t) => t.id));
  const toReset = new Set<string>();
  const findDependents = (parentId: string) => {
    for (const t of allTasks) {
      if (t.depends_on.includes(parentId) && doneIds.has(t.id)) {
        toReset.add(t.id);
        findDependents(t.id);
      }
    }
  };
  findDependents(taskId);
  for (const dependentId of toReset) { appendTaskEvent(... 'reset' ...); }
}
```

**Flow:** append `reset` for the root FIRST (so it appears before dependents' resets in the log), then walk dependents transitively — but ONLY tasks whose status is currently done get added (a blocked/in_progress dependent keeps its claim; its state was never validated by completion). Each dependent gets its own timestamped reset event.
**Invariant:** The done-set is snapshotted from `getAllTasks` BEFORE any dependent resets are appended — otherwise resetting A would remove it from done and skip B-depends-on-A. Recursion is unguarded against cycles but safe in practice because membership in `toReset` doesn't stop re-visits... actually it re-walks harmlessly since appends happen once per id in the final loop over the SET. Porters must keep collect-then-append ordering or replay order changes semantics.
**Probe:** direct tests `tests/swarm/task-actions.test.ts::cascade-reset resets dependent tasks` (:161) and `::reset single task` (:132); `grep -c "findDependents" swarm/task-store/commands.ts` (=3: def + 2 calls).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-messenger-swarm", query: "resetTask cascade findDependents doneIds", limit: 5 });
```

## Verdict
Adopt snapshot-done-set-then-transitive-collect-then-append as THE cascade algorithm; adapt "which statuses count as invalidated" to your domain; omit cascade entirely for linear pipelines.

<!-- capsule-v2 -->
# Markdown mutation lock — canonical-path-keyed cross-process mutex with poll-then-throw semantics

**Source:** pi-hermes-memory (MIT, `main@26f0acaa7741a81ea28eb992ab7ffcfdb7b50a0c`); Codebase Memory `pi-hermes-memory`. **Question:** Two processes may edit the same MEMORY.md / USER.md / failures.md at once — how do you make every read-modify-write of one file mutually exclusive across sessions without flock?

## acquireMarkdownMutationLock / withMarkdownMutationLock
**Path/Symbol:** `src/store/markdown-mutation-lock.ts` (whole file, 38 L): `MUTATION_WAIT_MS = 5_000` (:5), `MUTATION_STALE_MS = 300_000` (:6), `canonicalMarkdownIdentity` (:8–10), `acquireMarkdownMutationLock` (:12–29), `withMarkdownMutationLock` (:31–38); depends on `AtomicLockCoordinator.shared` (atomic-lock-coordinator.md) and `canonicalStoragePath`.
**Signature:** `withMarkdownMutationLock<T>(filePath, op: () => Promise<T> | T): Promise<T>`; `acquireMarkdownMutationLock(filePath) → AtomicLockLease`.
**Data Shape:** lock key = `` `mutation:${canonicalStoragePath(filePath)}` `` — canonicalized (symlinks resolved) so `/path/./MEMORY.md`, alias paths, and symlinked storage dirs map to ONE key.

### Decisive source
```ts
export async function acquireMarkdownMutationLock(filePath: string): Promise<AtomicLockLease> {
  const identity = await canonicalMarkdownIdentity(filePath);
  const coordinatorDir = path.dirname(path.dirname(identity));
  // ^ coordinator DB lives TWO levels above the file: ~/.pi/agent/.pi-hermes-locks.sqlite,
  //   so global files AND every projects-memory/<name>/MEMORY.md share one coordinator
  const coordinator = AtomicLockCoordinator.shared(path.join(coordinatorDir, ".pi-hermes-locks.sqlite"));
  const lockKey = `mutation:${identity}`;
  const deadline = Date.now() + MUTATION_WAIT_MS;
  let lease = coordinator.tryAcquire(lockKey, { staleMs: MUTATION_STALE_MS });
  while (!lease) {
    if (Date.now() >= deadline) {
      throw new Error(`Memory mutation already in progress for ${identity}`);   // THROW, not defer
    }
    await new Promise((resolve) => setTimeout(resolve, 10));                    // 10 ms poll
    lease = coordinator.tryAcquire(lockKey, { staleMs: MUTATION_STALE_MS });
  }
  return lease;
}
```

**Flow:** (1) resolve the file to its canonical identity; (2) acquire via the shared SQLite coordinator with a 5 s poll deadline; (3) on timeout THROW — the caller surfaces "already in progress" as a normal tool error; (4) `withMarkdownMutationLock` releases in `finally`. Consumers: `StandingInstructions.mutate`, `sync-markdown-memories.reconcileFile` (per-file scope), and MemoryStore writes (via the same helper).
**Invariant:** the wait is SHORT and ends in a thrown error, not a queue — memory edits are interactive operations where blocking for minutes would be worse than a visible collision error; contrast `consolidation-lock-ladder.md`, where waiting is fine and loss returns `deferred`. The stale window is LONG (300 s) because a legitimate Markdown write is fast but a crashed process must still be reclaimable. The two-levels-up DB placement makes the lock domain cover both global and project stores with a single coordinator instance.
**Probe:** `tests/store/markdown-mutation-lock.test.ts` — asserts mutual exclusion between concurrent acquisitions of the same path, the throw-on-timeout message carrying the canonical identity, and release allowing reacquisition. Coverage caveat: tests/ excluded from the graph index.
**Retrieve:** `search_graph({ project: "pi-hermes-memory", query: "acquireMarkdownMutationLock withMarkdownMutationLock MUTATION_STALE_MS", limit: 5 })`

## Verdict
Adopt for any human-editable file mutated by multiple agent processes. Adapt wait/stale constants and the coordinator placement rule to the host layout. Omit nothing — the whole primitive is 38 lines whose value is the three decisions: canonical keying, shared-coordinator placement, poll-then-throw.

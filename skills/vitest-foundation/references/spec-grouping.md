<!-- capsule-v2 -->
# Spec grouping — how are test specifications partitioned into ordered worker groups with correct parallelism and batching rules?

**Source:** Vitest (`vitest-dev/vitest`, MIT, `main@cf9176bf`); Codebase Memory `vitest`. **Question:** How does the node layer turn a flat spec list into groups that (a) honor `sequence.groupOrder`, (b) never batch files that would share one VM context, and (c) keep typecheck and sequential specs isolated?

## `groupSpecs` in the pool factory
**Path/Symbol:** `packages/vitest/src/node/pool.ts:groupSpecs` (349–460); consumed by `createPool.executeTests` (60–227) which iterates groups with `pool.setMaxWorkers(group.maxWorkers)` per group.
**Signature:** `function groupSpecs(specs: TestSpecification[], environments: WeakMap<TestSpecification, ContextTestEnvironment>)` → `Groups[]` where `Groups = { specs: SpecsForRunner[]; maxWorkers: number; typecheck?: boolean }` and `SpecsForRunner = TestSpecification[]` (one element = one worker run request, except typecheck / `--maxWorker=1 --no-isolate`).
**Data Shape:** sparse array indexed by `sequence.groupOrder`; a trailing `sequential` group (isolate=true + order 0 + maxWorkers 1) appended LAST; a `typechecks` record keyed by project name appended after all normal groups.

### Decisive source
```ts
// Non-isolated single worker can receive all files at once.
// vm pools are excluded: their `isolate: false` comes from config
// resolution rather than the user, because their isolation is a fresh VM
// context per run request — batching files into a single run request
// would share one context across all of them.
if (isolate === false && maxWorkers === 1 && spec.pool !== 'vmThreads' && spec.pool !== 'vmForks') {
  const previous = groups[order].specs[0]?.[0]
  if (previous && previous.project.name === spec.project.name && isEqualEnvironments(spec, previous)) {
    return groups[order].specs[0].push(spec)
  }
}
```
Plus the maxWorkers-conflict guard:
```ts
const maxWorkers = resolveMaxWorkers(spec.project)
groups[order] ||= { specs: [], maxWorkers }
// Multiple projects with different maxWorkers but same groupOrder
if (groups[order].maxWorkers !== maxWorkers) {
  throw new Error(`Projects "${last}" and "${spec.project.name}" have different 'maxWorkers' but same 'sequence.groupOrder'.\nProvide unique 'sequence.groupOrder' for them.`)
}
```

**Flow:** shard via sequencer → sort → for each spec: typecheck specs collect per-project; sequential-candidate specs (`isolate===true && order===0 && maxWorkers===1`) go to their own single-worker group; otherwise bucket by `groupOrder`, computing `resolveMaxWorkers` (project override → global override → watch ? cpus/2 : cpus-1) — batching into ONE run request happens only when isolate=false AND maxWorkers=1 AND not a vm pool AND same project AND serialized-environment-equal (`JSON.stringify(env.options)` compare) → after the loop, typecheck groups then the sequential group are appended.

**Invariant:** (1) vm-pool specs NEVER batch into a shared run request even though their resolved config says `isolate: false` — each needs a fresh VM context; (2) different `maxWorkers` under the same `groupOrder` is a loud config error, not silent serialization; (3) environment equality is decided by name + serialized options, cached per environment object; (4) groups run strictly in array order (`Promise.allSettled` per group before the next starts) so groupOrder is a real execution barrier.

**Probe:** `test/e2e/test/group-order.test.ts` (:4–53) — three projects declared in reverse order with `sequence.groupOrder` 1/2/3; asserts execution order via stdout snapshot (`|3|` first). `test/e2e/test/workers-option.test.ts` covers maxWorkers resolution.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "vitest", query: "groupSpecs sequence.groupOrder maxWorkers isolate", limit: 10, fields: ["signature", "name", "file"] });
// resolves: vitest.packages.vitest.src.node.pool.groupSpecs
```

## Verdict
Adopt groupOrder barriers, the loud maxWorkers conflict error, sequential-group isolation, and especially the vm-pool no-batch exception. Adapt worker-count defaults and environment serialization to the host. Omit browser-spec side-channel handling (`browserSpecs` routed to a lazily created separate pool) unless the host has an in-browser runner.

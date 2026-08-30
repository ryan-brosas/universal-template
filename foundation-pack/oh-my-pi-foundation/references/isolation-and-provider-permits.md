<!-- capsule-v2 -->
# Task isolation — isolate Git state and cap only network production

**Source:** Oh My Pi MIT `main@96f428097`; Codebase Memory project `oh-my-pi`. **Path:** `packages/coding-agent/src/task/{worktree,provider-concurrency}.ts`. **Question:** How do parallel coding workers avoid both Git cross-talk and provider-cap deadlock?

## Source contract
**Path/Symbol:** `worktree.ts:ensureIsolation` (482–535), `cleanupIsolation` (538+), `isolation-ownership.ts:writeIsolationOwner`; `provider-concurrency.ts:wrapStreamFnWithProviderConcurrency` (76–104).
**Signature:** `ensureIsolation(baseCwd, id, preferred?): Promise<IsolationHandle>`; stream wrapper retains a provider permit until producer completion.
**Data Shape:** owned isolation marker, detached Git directory, shared per-provider resizable semaphore, event stream, `IsolationHandle { mergedDir, backend, fellBack, fallbackReason }`.

### Decisive source
```ts
// Claim ownership before the backend materialises `m`. Backends only
// create/replace `mergedDir` … so the marker survives `isoStart` — and a
// concurrent `omp worktree clear` never sees this sandbox without a live
// owner, even while a large clone is still in progress.
await fs.mkdir(baseDir, { recursive: true });
await writeIsolationOwner(baseDir, id);
await natives.isoStart(candidate, repoRoot, mergedDir);
// Sever the isolation's git metadata from the source checkout. … Detaching
// gives each isolation a private, frozen repo that still borrows the source
// object DB via alternates.
await git.detachGitDir(mergedDir, sourceCommonDir);
```

```ts
const stream = await base(model, context, options);
// EventStream.result() settles when the producer pushes 'done'/'error'
// or calls fail() — i.e. once the provider has finished producing.
// Releasing here keeps the slot held for the network request and nothing else.
stream.result().then(release, release);
```

**Flow:** resolve repo root + common dir → try backend candidates in order (rm base dir between attempts) → claim ownership marker BEFORE materialization → start fallback-capable isolation → detach Git metadata (copy backends duplicate `.git` verbatim; a linked-worktree pointer would share HEAD/index/ref namespace) → run child. The provider limiter wraps ONE LLM request — release fires on producer settle or wrapper throw, never on conversation end.

**Invariant:** a child cannot mutate the parent Git HEAD/index/refs; parents release provider capacity before tool-spawned children need it, preventing width-over-cap deadlock (regression `#3749`); an unavailable backend falls through candidates with the reason retained.

**Probe:** direct `task-spawn.test.ts:151–275` covers permit ownership; provider module documents the spawn-tree deadlock regression `#3749`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.check_index_coverage({ project: "oh-my-pi", paths: ["packages/coding-agent/src/task/worktree.ts", "packages/coding-agent/src/task/provider-concurrency.ts"] });
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", name_pattern: "^(ensureIsolation|cleanupIsolation|wrapStreamFnWithProviderConcurrency)$", limit: 8, fields: ["signature"] });
```

## Verdict
Adopt own-before-materialize sandbox markers, git-dir detachment with alternates, and request-scoped (not conversation-scoped) provider permits; adapt backend kinds and semaphore sizing to host runtimes; omit overlay/copy backend specifics unless porting the isolation layer.

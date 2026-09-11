<!-- capsule-v2 -->
# Autoresearch — experiments belong to a branch and a durable ledger

**Source:** Oh My Pi MIT `main@96f428097`; Codebase Memory project `oh-my-pi`. **Path:** `packages/coding-agent/src/autoresearch/{index,git,state,storage}.ts`. **Question:** How can an agent experiment repeatedly without destroying a user worktree or reviving runs on the wrong branch?

## Source contract
**Path/Symbol:** `autoresearch/git.ts:ensureAutoresearchBranch` (36–97), extension rehydrate in `index.ts` (52–76: `reconstructControlState`, `onActiveBranch`, `buildExperimentState`), `state.ts:buildExperimentState/reconstructControlState`.
**Signature:** `ensureAutoresearchBranch(api, workDir, goal): Result`; `reconstructControlState(entries): state`.
**Data Shape:** clean Git baseline, `autoresearch/*` branch, persisted control entries, SQLite session/run rows, current segment metrics.

### Decisive source
```ts
if (dirtyPaths.length > 0) return { ok: false, error: "Worktree is dirty ... clean baseline." };
const onActiveBranch = session === null || session.branch === null || session.branch === currentBranch;
runtime.autoresearchMode = control.autoresearchMode && onActiveBranch;
if (!everActivated) { /* do not create storage just to inspect */ }
```

**Flow:** reject pure-JJ/dirty unsafe branch setup → create or reuse isolated branch → rehydrate ONLY when the current branch matches → reconstruct state from durable control + logged runs → enable experiment tools.

**Invariant:** switching branches detaches experiment tools instead of mixing ledgers (`mode = enabled && onActiveBranch`); inactive sessions never create persistent storage as a side effect of inspection.

**Probe:** direct `test/autoresearch-git.test.ts:49–142` protects pure-JJ and nested roots while allowing colocated/plain Git; `autoresearch-before-agent-start.test.ts` covers prompt injection. Coverage caveat: tests excluded from graph index by design.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", name_pattern: "^(buildExperimentState|reconstructControlState|ensureAutoresearchBranch)$", limit: 8, fields: ["signature"] });
await mcp.codebase_memory.get_code_snippet({ project: "oh-my-pi", qualified_name: "oh-my-pi.packages.coding-agent.src.autoresearch.state.buildExperimentState" });
```

## Verdict
Adopt branch-bound experiment identity with durable control entries and inspect-without-create laziness; adapt branch naming and storage backends to host; omit the specific JJ/Git edge list unless porting the VCS guard.

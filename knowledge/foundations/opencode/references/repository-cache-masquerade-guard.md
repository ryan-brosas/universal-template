<!-- capsule-v2 -->
# RepositoryCache masquerade guard — when may an existing checkout be reused as a cache entry?

**Source:** opencode MIT `dev@03521003fafd`; Codebase Memory `opencode`. **Question:** when a remote-reference cache resolves a local path, how does it avoid treating an enclosing repository (git discovery walks upward) as the cached checkout?

## Connected graph-selected seam
**Path/Symbol:** `packages/core/src/repository-cache.ts`: `ensure` (layer body, ~:155-250), reuse predicate; `packages/core/src/repository.ts`: `cachePath` (:126-131), `validateBranch` (:105-112), `same` (:135-137).
**Signature:** `ensure: (input: {reference: Repository.RemoteReference, refresh?: boolean, branch?: string}) => Effect<Result, Error>`.
**Data Shape:** `Result = {repository, host, remote, localPath, status: "cached"|"cloned"|"refreshed", head?, branch?}`; 8-class typed error union plus `LockFailedError` wrapping any non-domain flock error.

### Decisive source
```ts
// Discovery walks upward, so an enclosing repository with a
// matching origin could masquerade as the cache entry; reuse
// requires the checkout to live exactly at the cache path.
const worktree = existing ? yield* fs.resolve(localPath) : undefined
const reuse = Boolean(
  existing &&
    existing.worktree === worktree &&
    originReference &&
    Repository.same(originReference, cloneTarget),
)
if (!reuse && (yield* fs.existsSafe(localPath))) {
  yield* cacheOperation(fs.remove(localPath, { recursive: true }), "remove stale cache", localPath)
}
```

**Flow:** validate branch (charset regex: `[A-Za-z0-9/_.-]+`, no leading `-`, no `..`) → compute `cachePath` (host+segments, branch percent-encoded because names may contain `/`: `repo@feature%2Fx`) → under `flock.withLock("repository-cache:<localPath>")`: ensure parent dir → discover repo at path → reuse only if discovered worktree is EXACTLY the cache path AND origin identity matches → else remove-and-reclone → refresh path = fetch + `checkoutRemoteBranch` + `resetHard origin/<branch>` (self-heals a checkout left on another branch) → re-discover and report head/branch.
**Invariant:** content follows "newest wins" — a refresh may hard-reset the checkout while readers hold it; reuse must never trust an enclosing repo (worktree identity check) and branch-keyed checkouts are isolated from branchless ones (separate cache dirs, pinned by test).
**Probe:** `packages/core/test/repository-cache.test.ts` (7 it.live: stale-dir replacement, concurrent ensure → ["cached","cloned"] under one lock, origin-mismatch replacement, branch isolation `repo@feature`, enclosing-repo masquerade rejection, typed InvalidRepository/InvalidBranch/CloneFailed errors).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase-memory.search_graph({ project: "opencode", query: "RepositoryCache ensure reuse worktree masquerade", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-condition reuse rule (worktree == cache path AND origin identity match) for any cache that resolves through upward git discovery; adopt percent-encoding of branch segments in cache keys. Adapt the flock primitive to your host (any cross-process lock works; the lock key is the local path). Omit the specific git sync ladder if your host has no checkout step. Coverage caveat: Codebase Memory MCP not connected this pass — source+test reading fallback per AGENTS.md; no graph coverage check executed.

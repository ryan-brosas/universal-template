<!-- capsule-v2 -->
# Snapshot/undo — a shadow git repo per worktree for AI-edit rollback

**Source:** opencode MIT `<branch>@<commit>`; Codebase Memory `opencode`. **Question:** how does an AI edit session get undoable without copying the repo or re-hashing every blob?

## Connected graph-selected seam
**Path/Symbol:** `packages/opencode/src/snapshot/index.ts` (807 lines): config/constants (:26-33), state+git wrapper (:66-90), ignore sync (:118-146), object-database seeding (:148-186), `add` (:188-260), cleanup (:262-281), `track` (:283+).
**Signature:** `track()` (pre-edit) inits the shadow repo, syncs excludes, then `add --all --sparse --pathspec-from-file=- --pathspec-file-nul` of tracked-modified ∪ untracked-not-ignored minus oversized; returns a hash marking the state. Revert applies extracted patches in reverse.
**Data Shape:** hidden git repo in global data (`~/.opencode`-style) keyed `snapshot/<projectId>/<hash(worktree)>`, with `--work-tree` pointed at the real worktree; config `prune="7.days"`, `limit=2MB`.

### Decisive source
```ts
// Object-database SHARING via alternates: on huge repos, git add --all re-hashing
// blobs takes minutes. The shadow repo chains the source repo's objects dir
// into its own info/alternates, seeding the source index file. (:148-186)
// Newly-ignored files are DROPPED, not just skipped:
//   check-ignore --no-index keeps evaluation PATTERN-BASED even for tracked paths
```

**Flow:** every AI edit session can be rolled back via a shadow git repo keyed per worktree hash (multiple checkouts don't collide). Object-database sharing via `info/alternates` avoids re-hashing (best-effort; incompatible index falls back to full add). Newly-ignored files are `rm --cached` from the shadow index to prevent re-adding. Large files (>2MB) excluded via `info/exclude`. NUL-delimited pathspec files with `:(top,literal)` magic survive glob/newline filenames. `Semaphore(1)` per gitdir serializes concurrent sessions sharing one worktree. `gc --prune=7.days` bounds shadow growth.
**Invariant:** every snapshot failure degrades to `logWarning` — undo infrastructure must never break the actual task; enabled only when project vcs == git AND config `snapshot !== false`.
**Probe:** `packages/opencode/test/snapshot/snapshot.test.ts` (track → mutate → revert restores the pre-edit state; oversized files excluded from snapshot; newly-ignored file dropped from the shadow index).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "snapshot track revert shadow git alternates worktree", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the shadow-git-repo undo model with object-database sharing via alternates (reuse, never re-hash), active ignore-drift correction, and non-fatal failure contract; adapt the global data location and prune/limit config to host; omit the Effect-TS service wiring unless the target uses Effect.

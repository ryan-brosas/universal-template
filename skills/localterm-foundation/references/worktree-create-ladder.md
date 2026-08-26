<!-- capsule-v2 -->
# Worktree creation ladder — how do you mint fresh linked worktrees on a fresh base ref or a PR head without colliding names, and degrade when the remote is unusable?

**Source:** localterm MIT `fix/pi-extension-native-import@f26c5853`; Codebase Memory `localterm`. **Question:** How do you turn "new worktree" into concrete `git worktree add` invocations that branch from origin/HEAD (or `pull/<N>/head`), retry name collisions with memorable phrases, and never leave a half-created checkout?

## Base-ref degradation + adjective-noun retry
**Path/Symbol:** `packages/server/src/git-worktrees.ts:createGitWorktree` (:326–378), `resolveFreshStartRef` (:268–290), `fetchPullRequestHead` (:296–315), `ensureProjectFolder` (:81–109); `packages/server/src/utils/worktree-names.ts:generateWorktreeName` (:148–158).
**Signature:** `createGitWorktree(cwd, options: { baseRef?: "fresh"|"head", pullRequestNumber?: number }): Promise<{ path, branch, copiedFiles }>`.
**Data Shape:** PR creates are deterministic (`pr-<N>` branch + folder); auto names match `/^[a-z]+-[a-z]+(-\d+)?$/`; failure shape is a single `WorktreeError` carrying git's own stderr for the route to surface.

### Decisive source
```ts
const startRef = options.baseRef === "head" ? null : await resolveFreshStartRef(cwd);

let lastError: WorktreeError | null = null;
const attempted = new Set<string>();
for (let attempt = 0; attempt < MAX_WORKTREE_NAME_ATTEMPTS; attempt++) {
  const name = generateWorktreeName(attempted);
  attempted.add(name);
  const targetPath = path.join(projectDir, name);
  const args = startRef
    ? ["worktree", "add", "-b", name, targetPath, startRef]
    : ["worktree", "add", "-b", name, targetPath];
  const result = await runGit(cwd, args);
  if (result.exitCode === 0) {
    const copiedFiles = await copyWorktreeIncludes(mainRoot, targetPath);
    return { path: targetPath, branch: name, copiedFiles };
  }
  const stderr = result.stderr.trim();
  // A "fresh" start ref that was resolvable seconds ago may have raced (a
  // force-push, a branch deletion); once it's gone, retrying with a new
  // adjective-noun name won't help, so surface immediately.
  if (startRef && !/already exists/i.test(stderr)) {
    throw new WorktreeError(stderr || "git worktree add failed");
  }
  if (/already exists/i.test(stderr)) {
    lastError = new WorktreeError(stderr);
    continue;
  }
  throw new WorktreeError(stderr || "git worktree add failed");
}
```
Fresh-ref resolution with bounded fetch:
```ts
const direct = await readOriginHead();
if (direct) return direct;
// origin/HEAD isn't set locally. A bounded fetch lets origin set it ... Bounded by GIT_SPAWN_TIMEOUT_MS + GIT_TERMINAL_PROMPT=0,
// so a dead/unauthenticated remote degrades to local HEAD below.
const fetch = await runGit(cwd, ["fetch", "--no-tags", "--no-recurse-submodules", "origin"]);
if (fetch.exitCode === 0) {
  const afterFetch = await readOriginHead();
  if (afterFetch) return afterFetch;
}
return null;
```

**Flow:** anchor mainRoot → claim/derive project folder (bare name, else `<name>-<hash6>` sibling, marker-file owned; idempotent re-claim writes the marker again) → PR branch? fetch `pull/<N>/head`, resolve `FETCH_HEAD` IMMEDIATELY (next fetch clobbers it), add on `pr-<N>` → otherwise resolve fresh ref (origin/HEAD symbolic-ref → rev-parse verify → one bounded fetch → retry read → else null = branch from local HEAD) → up to 50 attempts of generate-name/add/retry-on-"already exists" → after git success run the include copy whose failure CANNOT fail the create.
**Invariant:** Retry only collision errors; any other stderr while holding a fresh startRef surfaces immediately because renaming can't fix a raced-away ref. `null` startRef is meaningful — it means HEAD, not an error, preserving no-remote behavior identical to pre-config creates. FETCH_HEAD must be pinned to a sha in the same breath as the fetch.
**Probe:** `packages/server/tests/git-worktrees.test.ts` — "creates a worktree under ~/.localterm/worktrees/<project>/ on a memorable branch name" :162–181 (branch regex + path join + file present); "creates two worktrees with distinct memorable names" :183–201; "puts same-named repos in distinct project folders" :203–246 (two repos named `same-name` get disjoint folders); "baseRef head branches from local HEAD…no copied files" :250–267; "creates a pr-<N> worktree from pull/<N>/head against a local bare origin" :269–298 (`update-ref refs/pull/42/head` fixture); "surfaces a clear error when a PR head can't be fetched (no origin)" :300–317 (nothing created). Executed this pass: 13/13 green.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.trace_path({ project: "localterm", function_name: "localterm.packages.server.src.git-worktrees.createGitWorktree", direction: "inbound", depth: 3 });
```
Executed live pre-write: callers_total 6 — hop1 `buildApiRoutes`, hop2 `createServer` (route layer is the sole real consumer); `search_graph("git worktree service create list include-file")` ranks `createGitWorktree` :326–378, `resolveFreshStartRef` :268–290, `fetchPullRequestHead` :296–315 line-exact.

## Verdict
Adopt the ladder: fresh-ref degradation chain, collision-only retries seeded with attempted names, immediate surfacing of non-collision errors, post-success best-effort copy; adapt the name word-list and MAX attempts to taste, and your PR provider beyond GitHub's well-known `pull/<N>/head` refspec; omit the project-folder marker scheme if your host has no same-named-repo collision problem. Trap: treating an empty model/base resolution as an error — here null is a deliberate "use local HEAD" so offline repos still create.

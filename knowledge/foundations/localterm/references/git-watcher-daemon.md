<!-- capsule-v2 -->
# Daemon-global git watcher — how do I detect commits in ANY repo under a directory tree, from any process, without per-session PTY hooks?

**Source:** localterm MIT `fix/pi-extension-native-import@f26c5853f4bed28f7a0cca14dd1c02f54b86d6fa`; Codebase Memory `localterm`. **Question:** How do I turn recursive fs.watch noise into classified git ref events per affected repo — including repos created after the watch armed?

## sync-reconciled watchers + eager seed + empty-baseline discovery
**Path/Symbol:** `packages/server/src/automation-git-watcher.ts:AutomationGitWatcher.sync` (148–163), `.discoverExistingRepos` (196–216), `.onFsEvent` (218–231), `.route` (233–249), `.classify` (261–272); throttle `packages/server/src/utils/throttle.ts:Throttle` (leading-edge + trailing flush).
**Signature:** `sync(automations: Automation[]): void` (idempotent reconcile); emits `refEvent: [eventName: GitRefEventName, repoRoot: string]`.
**Data Shape:** `entries: Map<cwd, {handle, repos: Map<gitDir, {repoRoot, snapshot: GitSnapshot|null, throttle}>>}` keyed by RESOLVED gitDir so worktrees/submodules sharing a `.git` share one state.

### Decisive source
```ts
// :241-246 — repo that appeared mid-watch with refs already present
state = this.seedRepo(entry, gitDir, repoRoot);
if (state.snapshot && state.snapshot.refs.size > 0) {
  for (const eventName of classifyGitChanges(EMPTY_GIT_SNAPSHOT, state.snapshot)) {
    this.emit("refEvent", eventName, repoRoot);
  }
}
```

**Flow:** `sync` recomputes the desired cwd set (enabled ∧ lifecycle active ∧ selects ≥1 git event) and starts/stops watchers to match — cheap enough to call after EVERY automation mutation. Arming does an eager walk that STOPS DESCENDING at the first `.git` (the recursive watch covers working-tree changes; nesting would re-traverse 20k dirs) and skips `node_modules`, seeding baseline snapshots so the first post-arm change classifies against real pre-state. Event filter ladder: filename null ⇒ drop → resolve against watched cwd → cheap substring rejects (`/.git/` boundary check, then `/node_modules/`) BEFORE any stat-ing → `resolveGitDir(dirname)` routes to the owning repo's throttle. Classification = leading-edge emit on first `.git` event of a burst + one trailing flush re-snapshot (GIT_DIRTY_THROTTLE_MS) so post-commit final state is always classified; snapshots swap-then-diff (`previous || current` null ⇒ skip). A bare `git init` seeds silently (no refs); `init`+first-commit in ONE fs.watch batch has no pre-state, so the refs that "appeared" are emitted against EMPTY_GIT_SNAPSHOT.
**Invariant:** this watcher is source-agnostic (catches commits from editors/SSH/headless agents where shell-hook gaps hide them) but fires only for event automations; the PER-SESSION GitDiffWatcher stays the live-tab path, and internal `git-dirty` is filtered out of user-selectable events. Watch failures (missing dir, inotify limits) are swallowed at arm but eager-seeding still runs; a later sync retries.
**Probe:** `packages/server/tests/automation-git-watcher.test.ts` — `"classifies a subsequent commit on an existing repo as git-commit"` (:108, fake-watch injected so no real fs timing), `"emits git-branch-change when a new repo appears with a commit in a single batch"` (:154), `"ignores a repo under node_modules..."` (:202), `"routes concurrent commits in sibling repos to the right repoRoot"` (:218), `"arms a watcher only for event automations that select a git event"` (:239). Integration twin: `automation-git-watcher-integration.test.ts`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "localterm", query: "AutomationGitWatcher sync seedRepo route classify", limit: 6, detail: "compact" });
// → seedRepo @ automation-git-watcher.ts:251-259, classify @ :261-272, sync @ :148-163, route @ :233-249
```

## Verdict
Adopt the desired-set reconcile + eager-seed/lazy-discover + gitDir-keyed routing pattern verbatim for any fs.watch-over-many-repos problem; adapt the event vocabulary and throttle window to host; omit the empty-baseline branch only if late-created repos are impossible in your domain. 10 unit tests (fake-timer, injectable watch fn) + integration suite pin it at this commit.

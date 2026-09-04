<!-- capsule-v2 -->
# Progressive nested-repo disclosure — how does an umbrella workspace index clones only when work touches them?

**Source:** pi-fovea MIT `main@5bd4e6f`; Codebase Memory `mnt-hdd-utopia-inspo-pi-fovea`. **Question:** A root holding many nested git repos/submodules would blow the resident graph if fully indexed — how do you enroll exactly the ones work enters, and never leak facts from removed ones?

## Enrolled boundary set + first-edit trigger + marker-vanish purge
**Path/Symbol:** `src/core/state.ts:refreshState` disclosure block (:202-230, :240-260) + `src/core/build.ts:expandSubmodules/listFiles/readEnrolledBoundaries` (:138-198, :446-458).
**Signature:** `listFiles(root, routeRes?, enrolled: ReadonlySet<string> = NO_BOUNDARIES): Promise<string[]>` — listing crosses ONLY enrolled `.git`-marker boundaries; `readEnrolledBoundaries(root): Promise<string[]>` restores them from the fact-cache header.
**Data Shape:** `store.enrolled: Set<string>` of repo-relative boundary prefixes ("sub", "repo/deep"); persisted in cache header `enrolled?: string[]`; `MAX_SUBMODULE_DEPTH` env-clamped 1..16 (default 4).

### Decisive source
```ts
// A hint landing across a .git marker enrolls the boundary — every marker on
// the path, so doubly-nested clones cross together — and a vanished marker
// un-enrolls, so a removed clone leaves no orphan facts behind.
for (const boundary of [...store.enrolled]) {
  const exists = await stat(join(state.root, boundary, ".git")).then(() => true, () => false);
  if (!exists) { store.enrolled.delete(boundary); disclosureChanged = true; }
}
...
let prefix = "";
for (const seg of h.split("/").slice(0, -1)) {
  prefix = prefix ? `${prefix}/${seg}` : seg;
  if (store.enrolled.has(prefix)) continue;
  const boundary = await stat(join(state.root, prefix, ".git")).then(() => true, () => false);
  if (!boundary) continue;
  store.enrolled.add(prefix);
  disclosureChanged = true;
}
```

**Flow:** cold build lists only top-level files (any dir containing `.git` is opaque unless enrolled) → an edit hint or a collapsed porcelain drift entry crossing a marker walks EVERY path segment, enrolling each that bears a `.git` (doubly-nested clones enroll as a chain "repo" + "repo/deep") → `disclosureChanged` forces a relist → a directory-shaped probe change is itself an edit event (porcelain collapses submodule drift to the gitlink name) and auto-enrolls WITHOUT any hint → a deleted marker un-enrolls and its facts purge → enrollment survives process restarts via the fact-cache header.
**Invariant:** untouched clones stay closed forever (no background crawl); a gitlink path itself NEVER enters the file pipeline (it names a directory — pushing it through would fail stat and masquerade as unreadable); enrolled-but-unpopulated submodules degrade to empty silently.
**Probe:** `tests/workspace.test.ts` — "crosses exactly the enrolled boundaries in a plain umbrella" (:56-67); "enrolls a nested clone and its parent chain on the first edit hint" (:101-117, untouched repo2 stays closed); "auto-enrolls a submodule when drift lands inside without any hint" (:146-163); "un-enrolls a project whose marker vanished, purging its facts" (:164-180); "keeps submodule contents closed in a Git root until enrolled" (:69-85).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pi-fovea", query: "expandSubmodules listFiles enrolled boundaries", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt progressive disclosure for any indexer over multi-repo workspaces. Adapt the marker (`.git` presence covers both real clones and worktrees). Omit pi hint plumbing — any per-file event source triggers enrollment.

<!-- capsule-v2 -->
# Graph project re-registration — how do you keep a foundation leaf's Retrieve surface alive when the codebase-memory indexer re-registers the same repo under a new path-slugged project name?

**Source:** pi-fovea mining lane evidence at `main@5bd4e6f5c56190fb174245266464607b11f7a337`; Codebase Memory `mnt-hdd-utopia-inspo-pi-fovea`. **Question:** A leaf's every Retrieve block cites one graph project name; after a checkout move or MCP restart the same HEAD can come back registered under a DIFFERENT slugged name while old registrations vanish or go stale — what is the detection-and-repair ladder?

## Connected graph-selected seam
**Path/Symbol:** observed 2026-08-26 (pass 4): prior twin `mnt-hdd-utopia-inspo-pi-ecosystem-pi-fovea` (984n/3104e) vanished from `list_projects`; fresh FULL re-index of the SAME checkout/HEAD registered as `mnt-hdd-utopia-inspo-pi-fovea` (984n/3106e, parse_partial=0); legacy short-name `pi-fovea` (871n/2605e) persists serving the pre-drift v0.14.3 parse.
**Signature:** `index_status(project, {verbose: true}) → {root_path, git.head_sha, nodes, edges, parse_partial, skipped}`; `check_index_coverage(project, paths)`.
**Data Shape:** three coexisting surfaces per repo: legacy short-name (stale content), dead slugged twin (gone), live slugged twin (current). Node/edge counts differ slightly between twins of identical HEAD (3104→3106 edges) purely from indexer-version drift.

### Decisive source
```text
Detection ladder executed this pass:
1. list_projects            → is the cited name still registered?
2. index_status(verbose)    → does root_path AND head_sha match the leaf pin?
3. stale-content tell       → graph Module line-range vs disk wc -l on a clean
                              tree (session.ts recorded 1–61, disk showed 91;
              metadata_changed freshness flags agreed)
4. FULL re-index of the ONE existing checkout → new slugged registration
5. check_index_coverage     → zero parse_partial/skipped before citing
Repair: replace the dead project string across SKILL.md provenance/full-view
and EVERY reference Retrieve block; record old→new mapping + count delta.
```

**Flow:** cite-time verification catches the mismatch BEFORE any new citation → the live twin is identified by root_path + head_sha together (a matching sha string alone proved insufficient: the stale short-name carried the same HEAD string with older content) → repair sweeps all citations uniformly so the leaf never mixes two graph names.
**Invariant:** A graph result may be cited only from a project whose `root_path` equals the pinned checkout AND whose `head_sha` equals the pinned commit AND whose cited files report `no_recorded_issue` at current generation; when in doubt, source line-counts from the clean worktree outrank recorded ranges.
**Probe:** No upstream test pins MCP behavior (external service). Deterministic probe: run `list_projects`, confirm exactly one live project carries `root_path=/mnt/hdd/utopia/inspo/pi-fovea` with `head_sha=5bd4e6f…`, then `search_graph` a pin-era symbol (`syncScopeForPath`) — it must resolve only on the live twin.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pi-fovea", query: "syncScopeForPath observeSessionPaths session", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the five-step detection ladder and uniform-citation repair. Adapt project-name expectations to your indexer's slug scheme. Omit any attempt to rename or alias server-side registrations — repair lives entirely in the leaf's citation strings plus a provenance note recording the old→new mapping.

<!-- capsule-v2 -->
# Permission file store — how do permission requests/resolutions survive across processes, and what is the resolve ordering?

**Source:** locoagent (Claude Code CLI fork, MIT), rev `c01bb3f`; Codebase Memory `locoagent`. **Question:** what does the pending/→resolved/ directory protocol guarantee that a mailbox message alone cannot?

## lockfile-guarded write → resolve-writes-then-unlinks
**Path/Symbol:** `src/utils/swarm/permissionSync.ts:writePermissionRequest` (:215-250), `readPendingPermissions` (:256-312), `resolvePermission` (:360-443), `cleanupOldResolutions` (:452-517).
**Signature:** `resolvePermission(requestId, resolution: PermissionResolution, teamName?): Promise<boolean>`.
**Data Shape:** dirs `~/.claude/teams/{team}/permissions/{pending,resolved}`; request files `{id}.json` validated by `SwarmPermissionRequestSchema` (zod); a directory-level `.lock` file guards writers; reads sort oldest-first by createdAt.

### Decisive source
```ts
// Write to resolved directory
await writeFile(resolvedPath, jsonStringify(resolvedRequest, null, 2), 'utf-8')
// Remove from pending directory
await unlink(pendingPath)
```
Cleanup resilience (:495-504): unparseable resolution files are deleted anyway ("If we can't parse it, clean it up anyway") with deletion failures swallowed.

**Flow:** worker: ensurePermissionDirsAsync → lockfile.lock(pending/.lock) → write `{requestId}.json` into pending → release. Leader: readdir (ENOENT ⇒ []) → filter `.json` ≠ `.lock` → schema-validate each (invalid files logged and SKIPPED, never crash) → oldest-first UI ordering → resolvePermission re-locks, re-reads + re-validates the pending file, writes the enriched copy (status/resolvedBy/resolvedAt/feedback/updatedInput/permissionUpdates) to resolved/, THEN unlinks pending — all under the same lock.
**Invariant:** resolved-before-pending-delete ordering means a crash between the two leaves BOTH copies (duplicate-visible, never lost) — the same build-before-mark family as teammate-mailbox-delivery; every reader tolerates ENOENT and invalid JSON; workers poll readResolvedPermission until their ID appears.
**Probe:** coverage caveat (no direct tests). Deterministic probes: `grep -n 'Remove from pending directory' src/utils/swarm/permissionSync.ts` (:426); `grep -n "f !== '.lock'" src/utils/swarm/permissionSync.ts` (:280).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "writePermissionRequest resolvePermission readPendingPermissions SwarmPermissionRequestSchema", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt two-directory state machines with lockfile-guarded transitions and validate-per-read tolerance for cross-process stores; adapt paths; omit the legacy pollForResponse aliases unless you have old callers.

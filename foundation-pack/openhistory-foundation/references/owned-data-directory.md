<!-- capsule-v2 -->
# Owned data directory — how do I claim, adopt, and delete an on-disk data directory without ever touching one we don't own?

**Source:** OpenHistory MIT `main@daf7b073ce93673d0453d9f69b7435224c4bf49c`; Codebase Memory `openhistory`. **Question:** Before writing user activity data into a user-chosen directory, what gates prove the directory is ours, and how is deletion kept reversible until it must not be?

## Marker-gated ownership lifecycle
**Path/Symbol:** `src/main/data-directory.ts:ensureOwnedDataDirectory` (L19–42), `deleteOwnedDataDirectory` (L44–67), `safeDataDirectory` (L69–77), `assertOwnedMarker` (L79–86).
**Signature:** `ensureOwnedDataDirectory(candidate: string, options?: { adoptExistingUnmarked?: boolean }): string`; `deleteOwnedDataDirectory(candidate: string): void`.
**Data Shape:** Directory name must be exactly `activity-data` at depth ≥ 3 (`safeDataDirectory`). Ownership = presence of `.openhistory-data-root` containing exactly `"OpenHistory activity data v1\n"`. Options flag is the explicit adoption escape hatch.

### Decisive source
```ts
const directory = safeDataDirectory(candidate);
if (existed && lstatSync(directory).isSymbolicLink()) {
  throw new Error("OpenHistory data directory cannot be a symbolic link");
}
...
if (marked) {
  assertOwnedMarker(marker);          // exists, not symlink, exact content
} else if (existed && readdirSync(directory).length > 0 && !options.adoptExistingUnmarked) {
  throw new Error("Refusing to adopt a nonempty custom activity-data directory without explicit approval");
}
ensurePrivateDirectory(directory);
if (!marked) writePrivateFile(marker, DATA_ROOT_MARKER_CONTENT);
```

Delete side — quarantine rename first, recreate marker, only then destroy:
```ts
assertOwnedMarker(resolve(directory, DATA_ROOT_MARKER));
const quarantine = `${directory}.deleting-${process.pid}-${Date.now()}`;
renameSync(directory, quarantine);
try { ensurePrivateDirectory(directory); writePrivateFile(marker, CONTENT); }
catch (error) { renameSync(quarantine, directory); throw error; }   // rollback
try { rmSync(quarantine, { recursive: true, force: false }); }
catch (error) { rmSync(directory, ...); renameSync(quarantine, directory); throw error; }
```

**Flow:** resolve+shape-gate → symlink refusal → marker check (verify / adopt-gate / seed) → private perms → write marker → return. Delete: shape-gate → marker assert → rename to pid/timestamp quarantine → rebuild empty owned root → rm quarantine (rollback on any failure before or during).
**Invariant:** Every mutation happens only after content-verified ownership (`assertOwnedMarker` checks exact bytes, not just existence); symlinks are refused at both directory and marker level so `rm -r` can never follow out of the root; an unmarked nonempty directory is never adopted silently and never deleted (test asserts its files survive).
**Probe:** `src/main/data-directory.test.ts` — "refuses to delete an unowned directory and preserves its files" throws `/ownership marker/` and keeps `development-evaluation.json`; "refuses broad or ambiguously named deletion targets" rejects `/`. Executed this pass via repo runner: passing.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openhistory", query: "owned data directory ensure delete", limit: 10, fields: ["signature", "lines"] });
```

## Verdict
Adopt the marker-content contract, symlink refusal at every level, adoption gate, and quarantine-rename delete with rollback as-is. Adapt the required basename/depth rule and marker filename/content to your host's naming. Omit Electron-specific callers (`src/preload.deleteAllData`, renderer wiring). Coverage: all cited paths `no_recorded_issue`.

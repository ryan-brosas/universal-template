<!-- capsule-v2 -->
# DocStorageManager file layout — how the standalone file-based storage manager canonicalizes docNames, renames, and backs up .grist files

**Source:** grist-core Apache-2.0 `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** How does the non-hosted storage manager turn a docName into a canonical path, safely rename/delete, and make numbered backups?

## Canonical docName + exclusive rename + numbered backup
**Path/Symbol:** `app/server/lib/DocStorageManager.ts` — `getPath` (:39-44), `getCanonicalDocName` (:78-81), `renameDoc` (:141-159), `deleteDoc` (:113-132), `makeBackup` (:167-194), `_generateBackupFilePath` (:316-329), `_safeCopy` (:346-353), `listDocs` (:95-101).
**Signature:** `getPath(docName): string` appends `.grist` if absent and resolves against `_docsRoot`; `getCanonicalDocName(altDocName): Promise<string>`; `makeBackup(docName, backupTag): Promise<string>`.
**Data Shape:** canonical docName = basename (`.grist` stripped) for files directly in `_docsRoot`, else the realpath. Backup name = `${base}.grist.${YYYY-MM-DD}.${tag}.bak`, numbered with `-N` on collision.

### Decisive source
```ts
// getCanonicalDocName — basename only for docsRoot files, realpath otherwise
const p = await docUtils.realPath(this.getPath(altDocName));
return path.dirname(p) === this._docsRoot ? path.basename(p, ".grist") : p;
```
```ts
// renameDoc — exclusive-create then rename, tolerating same-file
return docUtils.createExclusive(newPath)
  .catch(async (e: any) => {
    if (e.code !== "EEXIST") { throw e; }
    const isSame = await docUtils.isSameFile(oldPath, newPath);
    if (!isSame) { throw e; }
  })
  .then(() => fse.rename(oldPath, newPath))
  .then(() => { this._sendDocListAction("renameDocs", oldPath, [oldName, newName]); });
```

**Flow:** `getPath` normalizes the extension and resolves against `_docsRoot`; `getCanonicalDocName` collapses a path to its basename when it lives directly in the docs root (clean URLs) and keeps the full realpath otherwise. `deleteDoc` refuses any path not ending in `.grist` (protects against wiping the disk/home) and either trashes or permanently removes. `renameDoc` uses exclusive-create to detect collisions, tolerating the same-file case, then renames and broadcasts a `renameDocs` doc-list action immediately (the comment notes the old delayed broadcast caused a chokidar remove-before-rename race). `makeBackup` generates a dated path, numbers it on collision, copies via `backupUsingBestConnection` (cooperative backup), and returns the final path.
**Invariant:** the `.grist`-extension guard in `deleteDoc` is a hard safety invariant — a porter must never delete a path that doesn't end in `.grist`. The canonical-name rule (basename vs realpath) is what keeps doc URLs clean and must be consistent across every storage method. `renameDoc`'s immediate broadcast is load-bearing (prevents the remove/rename race).
**Probe:** `test/server/lib/DocStorageManager.ts` exercises getPath/getCanonicalDocName/rename/delete/makeBackup; the backup path is covered by the cooperative-backup suite.
**Coverage caveat:** the chokidar race fix and the same-file rename tolerance are source-verified (behavior pinned by the rename tests).

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core", query: "DocStorageManager getCanonicalDocName renameDoc deleteDoc makeBackup getPath", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the canonical-name rule, the `.grist`-extension delete guard, exclusive-create rename with same-file tolerance, and the dated numbered-backup generator for any file-backed document store; adapt the root/backup naming; omit the doc-list broadcast if you have no live client list.

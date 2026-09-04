<!-- capsule-v2 -->
# Roots validation ladder — how do client-declared root URIs become safe working directories without letting one bad root kill the batch?

**Source:** modelcontextprotocol/servers MIT `main@76d64c822f5125032f89eb71dbdb94e42b434821` (src/filesystem); Codebase Memory `servers`. **Question:** What is the per-root validate-and-continue pipeline from `Root.uri` to a normalized directory allowlist?

## file:// → tilde-expand → resolve → realpath → isDirectory, per-item isolation
**Path/Symbol:** `src/filesystem/roots-utils.ts` (whole file: `parseRootUri` :13–25; error formatter :34–40; `getValidRootDirectories` :52–77). Direct test `src/filesystem/__tests__/roots-utils.test.ts` (84L).

**Signature:** `async getValidRootDirectories(requestedRoots: readonly Root[]): Promise<string[]>` — accepts SDK `Root { uri, name? }`; returns ONLY validated directories; failures log to stderr and CONTINUE. Per root: strip `file://` via `fileURLToPath` → expand `~`/`~/` → `path.resolve` → **`await fs.realpath`** → `normalizePath`.

### Decisive source
```ts
// src/filesystem/roots-utils.ts:13-25 — the per-root pipeline
const rawPath = rootUri.startsWith('file://') ? fileURLToPath(rootUri) : rootUri;
const expandedPath = rawPath.startsWith('~/') || rawPath === '~'
  ? path.join(os.homedir(), rawPath.slice(1)) : rawPath;
const absolutePath = path.resolve(expandedPath);
const resolvedPath = await fs.realpath(absolutePath);   // symlink resolution for security
return normalizePath(resolvedPath);                      // catch{} ⇒ null ⇒ "continue"
```

```ts
// :57-74 — per-item isolation in the caller loop
for (const requestedRoot of requestedRoots) {
  const resolvedPath = await parseRootUri(requestedRoot.uri);
  if (!resolvedPath) { console.error(...'invalid path or inaccessible'); continue; }
  const stats = await fs.stat(resolvedPath);
  if (stats.isDirectory()) validatedDirectories.push(resolvedPath);
  else console.error(...'non-directory root');            // file roots are skipped, not fatal
}
```

**Flow:** every root independently traverses the five-step ladder; any step throws ⇒ catch ⇒ null ⇒ stderr note + skip that root ONLY. Files masquerading as roots fail at the isDirectory gate; nonexistent paths fail at realpath; null-byte paths fail inside fileURLToPath/stat. Order of returned valid roots follows input order.

**Invariant:** symlink resolution happens BEFORE the directory check and BEFORE normalize — validating the unresolved path would let an attacker point a root at a sensitive dir through a benign-looking symlink (the same containment principle as `filesystem-sandbox`). One malformed root MUST NOT abort the batch: partial success with stderr diagnostics beats all-or-nothing startup.

**Probe:** `src/filesystem/__tests__/roots-utils.test.ts` — mixed batch of file:// URI, plain path, nameless plain path all resolve (:33–46); `./subdir/../subdir` collapses to the realpath'd subdir (:48–60); non-existent + file-not-dir + `\0null\0byte` roots are each rejected while the valid one survives (`toHaveLength(1)` :65–82).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "servers", query: "getValidRootDirectories parseRootUri realpath Root", limit: 10, fields: ["name", "file"] });
```

## Verdict
Adopt the five-step per-root ladder with per-item failure isolation and post-realpath normalization when consuming MCP roots or any client-supplied directory list; adapt logging destination to your host (roots themselves are deprecated SEP-2577 for NEW servers — see `deprecated-features-registry` — but the ladder applies to config-provided dirs identically); omit batch-abort on first invalid root and omit pre-realpath validation.

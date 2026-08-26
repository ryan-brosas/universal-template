<!-- capsule-v2 -->
# Artifact media scanner — how do run outputs get listed and read back without TOCTOU or path escape?

**Source:** dsh-factory MIT `main@3405edc7`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-dsh-factory`. **Question:** How do I expose files an agent produced under a checkout for browser review, safely against symlinks, escapes, and mid-read rewrites?

## scanArtifactMedia / artifactMediaData
**Path/Symbol:** `packages/domain/src/index.ts` (`containedPath`, `scanArtifactMedia`, `artifactMediaData`) (:128–131, :977–1027, :227–245).
**Signature:** `private async scanArtifactMedia(request): Promise<ScannedArtifactMedia[]>`; version = `` `${size}:${mtimeMs}` ``.
**Data Shape:** `.artifacts` dir under the selected run's checkout; allowlist map by extension (avif/gif/jpeg/jpg/png/webp images; m4v/mov/mp4/ogv/webm videos); caps default limit 100 files / 50MB each / 200MB total / depth 4.

### Decisive source
```ts
checkoutRoot = await realpath(checkout)
artifactRoot = await realpath(join(checkoutRoot, '.artifacts'))
...
if (!containedPath(checkoutRoot, artifactRoot)) throw new Error(`Factory artifact directory escapes checkout ${checkoutRoot}`)
...
let absolutePath: string
try { absolutePath = await realpath(unresolved); metadata = await stat(absolutePath) } catch ...
if (!containedPath(artifactRoot, absolutePath)) throw new Error(`Factory artifact media escapes .artifacts: ${path}`)
// read side — triple stat sandwich:
const before = await stat(item.absolutePath)
if (`${before.size}:${before.mtimeMs}` !== requested.version) throw ... 'changed before reading'
const data = await readFile(item.absolutePath)
const after = await stat(item.absolutePath)
if (`${after.size}:${after.mtimeMs}` !== requested.version || data.byteLength !== item.bytes) throw ... 'changed while reading'
```

**Flow:** resolve the run (explicit runId or latest-by-startedAt) → realpath BOTH checkout and `.artifacts` → containment check (relative-path not escaping parent) → BFS with sorted entries up to file/byte/depth caps, per-file realpath + containment re-check (symlink escape rejected) → listing returns metadata WITHOUT absolute paths → data reads verify the client-supplied size:mtime version BEFORE and AFTER reading plus byte-length equality.
**Invariant:** Every returned path is re-validated after resolution — a symlink planted inside `.artifacts` pointing outside is caught by the second `containedPath`; the stat-before/read/stat-after sandwich means a file replaced between listing and read fails loudly instead of serving mismatched bytes. ENOENT anywhere degrades to empty/skip, never crash.
**Probe:** `packages/domain/tests/domain.spec.ts` "lists image and video artifacts from the exact run checkout and reads only the listed revision" (listing from the exact run; stale-version read rejected). Deterministic from repo root: `grep -c 'containedPath' packages/domain/src/index.ts` = 3.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-dsh-factory", query: "artifactMediaData", limit: 5, fields: ["signature", "name", "file"] });
```
(CLI equivalent verified via sibling name-pattern queries on this project.)

## Verdict
Adopt realpath+containment at both levels and the version-sandwich read. Adapt extension allowlist to host media needs. Omit base64 data-URL transport shape if host streams instead.

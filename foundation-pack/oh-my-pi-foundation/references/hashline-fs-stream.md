<!-- capsule-v2 -->
# Hashline Filesystem seam + numbered streaming — raw text in, transformed text echoed back

**Source:** Oh My Pi MIT `main@96f428097`; Codebase Memory `oh-my-pi`. **Question:** How do you make a patch engine work over any backing store (disk, memory, LSP doc, VFS) while keeping snapshots, create-vs-update, and recovery honest?

## The seam: abstract ops over raw text only
**Path/Symbol:** `packages/hashline/src/fs.ts:Filesystem` (abstract, 66–126), `NotFoundError`, `isNotFound`, `InMemoryFilesystem` (~130), `NodeFilesystem` (~230).
**Signature:** `readText(path): Promise<string>`; `writeText(path, content): Promise<WriteResult>`; `exists(path): Promise<boolean>`; optional `readBinary?`, `preflightWrite`, `delete`, `move`; overridable `canonicalPath`, `allowTagPathRecovery`.
**Data Shape:** raw string lines for read/write; `WriteResult { text }` echoes the actual persisted bytes; missing path ⇒ throw `NotFoundError` (`code: "ENOENT"`) or anything `isNotFound` accepts — that is the ONLY create-vs-update signal; `preflightWriteOptions` carries `fileOp` for permission hints.

### Decisive source
```ts
export abstract class Filesystem {
  abstract readText(path: string): Promise<string>;
  async preflightWrite(_path: string, _options?: PreflightWriteOptions): Promise<void> {}
  /** Persist `content` at `path`. Returns the actual final text that was written. */
  abstract writeText(path: string, content: string): Promise<WriteResult>;
  async exists(path: string): Promise<boolean> {
    try { await this.readText(path); return true; }
    catch (error) { if (isNotFound(error)) return false; throw error; }
  }
  canonicalPath(path: string): string { return path; }
  allowTagPathRecovery(_authoredPath: string, _resolvedPath: boolean): boolean { return true; } // default allow
}
```

**Flow:** the patcher does all BOM strip + LF normalize between `readText` and `writeText` — the FS deals only in raw strings. Missing-file detection rides entirely on the notfound contract. `writeText` returns the *actual* text persisted so adapters that transform on serialization (notebooks, pretty-printers) can be cross-checked. `canonicalPath` is the key contract for snapshot caches — `NodeFilesystem` overrides it to absolute-ize so producers/consumers agree on the key.

**Invariant:** create-vs-update is decided purely by the notfound contract; a store is honest about what it actually wrote; `delete`/`move` are opt-in and default-throw rather than silently no-op.

**Probe:** `packages/hashline/test/patcher.test.ts` (Patcher mandatory/create-flow flows, tag path recovery), `file-ops.test.ts` + `fs.test.ts` (InMemory + Node adapters), `recovery.test.ts`.

## Tag-path recovery is a security gate, not just a convenience
**Path/Symbol:** `fs.ts:allowTagPathRecovery` (123–125 default); host override `packages/coding-agent/src/edit/hashline/filesystem.ts:HashlineFilesystem.allowTagPathRecovery` (95–110).
**Signature:** `allowTagPathRecovery(authoredPath, resolvedPath): boolean`.

### Decisive source (host override)
```ts
// Internal-URL authored targets (`local://`, `vault://`, …) are approved
// at the lower "read" privilege; never let one redirect onto a "write".
if (isInternalUrlPath(authoredPath)) return false;
// Confine the redirect to locations a plain "write" may legitimately target:
//  1. the working tree (the model dropped the directory), or
//  2. the session `local://` sandbox where plan/scratch artifacts live.
const root = canonicalSnapshotKey(this.session.cwd);
if (resolvedPath === root || resolvedPath.startsWith(`${root}${path.sep}`)) return true;
return targetsLocalSandbox(this.session, resolvedPath);
```

**Flow:** when an authored section path is missing but its snapshot tag uniquely names a file, `Patcher.prepare` may redirect reads AND writes to the tagged file. Hosts that grant write privilege by path shape override the default-allow gate to refuse redirects escalating beyond approval (internal-URL authored targets, out-of-tree resolved paths like secret vaults).

**Invariant:** a snapshot tag proves the model touched that exact content this session — it must never widen write scope; the gate decides per redirect before any read/write happens.

**Probe:** `test/patcher.test.ts::NoRecoveryFs` (a Filesystem whose `allowTagPathRecovery` refuses — recovery must stay off).

## Streaming numbered read — bounded chunks, no full-file materialization
**Path/Symbol:** `packages/hashline/src/stream.ts:streamHashLines` (95–132), `createChunkEmitter` (32), `resolveStreamOptions`.
**Signature:** `streamHashLines(source: ReadableStream<Uint8Array> | AsyncIterable<Uint8Array>, options?: StreamOptions): AsyncGenerator<string>` with `{ startLine?, maxChunkLines = 200, maxChunkBytes = 64 * 1024 }`.

### Decisive source
```ts
const wouldOverflow =
  outLines.length >= options.maxChunkLines || outBytes + sepBytes + lineBytes > options.maxChunkBytes;
if (outLines.length > 0 && wouldOverflow) { const flushed = flush(); if (flushed) chunks.push(flushed); }
outLines.push(formatted);
outBytes += (outLines.length === 1 ? 0 : 1) + lineBytes;
if (outLines.length >= options.maxChunkLines || outBytes >= options.maxChunkBytes) {
  const flushed = flush(); if (flushed) chunks.push(flushed);
}
```

**Flow:** input bytes decode as UTF-8 and split per line; each line LF-strips and numbers via `formatNumberedLine`; chunks emit lazily when either cap fires (whichever first). The generator never assembles the whole file — memory stays O(chunk). Coverage caveat: no dedicated direct test file for `streamHashLines` was found at HEAD (the overflow arithmetic is source-grounded only).

**Invariant:** long lines never block the stream; both caps are honored faithfully on both the pre-push look-ahead and post-push flush checks.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", name_pattern: "^(Filesystem|readText|writeText|canonicalPath|allowTagPathRecovery|streamHashLines|formatNumberedLine)$", limit: 16, fields: ["signature"] });
await mcp.codebase_memory.get_code_snippet({ project: "oh-my-pi", qualified_name: "oh-my-pi.packages.coding-agent.src.edit.hashline.filesystem.HashlineFilesystem.allowTagPathRecovery" });
```

## Verdict
Adopt raw-text-only FS seams, notfound-driven create-vs-update, echoed-write results, canonical snapshot keys, and the tag-recovery security gate with working-tree confinement; adapt path resolution, sandbox rules, and chunk caps to host; omit binary/move/delete extensions until a target needs them.

<!-- capsule-v2 -->
# Changed-file watcher — how are out-of-band file edits surfaced as diffs without false alarms or phantom deletions?

**Source:** locoagent (Claude Code CLI fork, rev `c01bb3f`); Codebase Memory `locoagent`. **Question:** mtime-gated re-read, diff-snippet extraction, and ENOENT-only eviction.

## getChangedFiles
**Path/Symbol:** `src/utils/attachments.ts:getChangedFiles` (:2063-2161), `isFileReadDenied` helper (:3986-3997).
**Signature:** `(toolUseContext) → Promise<Attachment[]>`; iterates `cacheKeys(readFileState)` in parallel.
**Data Shape:** per-path state `{ content, timestamp, offset?, limit? }`; emits `edited_text_file {filename, snippet}` or `edited_image_file {filename, content}`.

### Decisive source
```ts
// TODO: Implement offset/limit support for changed files
if (fileState.offset !== undefined || fileState.limit !== undefined) return null
const mtime = await getFileModificationTimeAsync(normalizedPath)
if (mtime <= fileState.timestamp) return null          // cheap gate first
const snippet = getSnippetForTwoFileDiff(fileState.content, result.data.file.content)
if (snippet === '') return null                        // touched but not modified
// ...
} catch (err) {
  // Evict ONLY on ENOENT (file truly deleted). Transient stat failures —
  // atomic-save races (editor writes tmp→rename and stat hits the gap),
  // EACCES churn, network-FS hiccups — must NOT evict, or the next Edit
  // fails code-6 even though the file still exists and the model just read
  // it. VS Code auto-save/format-on-save hits this race especially often.
  // See regression analysis on PR #18525.
  if (isENOENT(err)) toolUseContext.readFileState.delete(filePath)
  return null
}
```

**Flow:** every path the model has Read/Written/Edited → skip partial reads (offset/limit set) → skip read-denied paths → mtime gate → full `FileReadTool.call` → text files yield a minimal diff snippet (empty = untouched, drop); images re-read under the same token budget; notebook/pdf/parts explicitly `null`. Only true deletion evicts the cache entry.
**Invariant:** eviction is ENOENT-only — any other error leaves the entry intact so a transient failure can't make the next Edit demand a pointless re-read; "mtime changed" is necessary-but-insufficient (content-diff decides); partial-view entries must never enter diff comparison. Deny rules apply to WATCHING too, not just direct reads.
**Probe:** no upstream test (coverage caveat); PR #18525 rationale pinned verbatim :2145-2152. Deterministic probe: `sed -n '2145,2157p' src/utils/attachments.ts`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "getChangedFiles readFileState snippet two file diff ENOENT", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt mtime-gate + content-diff + ENOENT-only eviction for edit surfacing; adapt diff algorithm; omit IDE diagnostics siblings. Porting trap: evicting on ANY stat/read error breaks Edit flows during editor auto-save races; treating touch-without-change as an edit spams no-op snippets every turn.

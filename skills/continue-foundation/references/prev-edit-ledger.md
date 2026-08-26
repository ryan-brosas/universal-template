<!-- capsule-v2 -->
# Prev-edit ledger — how is the edit history that feeds next-edit prompts stored, expired, and fed forward?

**Source:** Continue (Apache-2.0) `main@5522c6f44ca0ac3528b37244818fbfa39b5af470`; Codebase Memory `continue`. **Question:** What are the exact eviction, forget, and store-rich/trim-later rules for previous edits, and why does each entry carry a random key suffix?

## 5-entry LRU with a session-forget ladder
**Path/Symbol:** `core/nextEdit/context/prevEditLruCache.ts` (whole, 30L) + `core/nextEdit/context/processNextEditData.ts:processNextEditData` (:43-151).
**Signature:** `setPrevEdit(edit: prevEdit): void`; `getPrevEditsDescending(): prevEdit[]`; `processNextEditData({...}): Promise<void>`.
**Data Shape:** `prevEdit = {unidiff, fileUri, workspaceUri, timestamp}`; QuickLRU keyed `` `${fileUri}:${timestamp}:${uniqueSuffix}` ``, maxSize **5**.

### Decisive source
```ts
// prevEditLruCache.ts
const maxPrevEdits = 5;
const uniqueSuffix = Math.random().toString(36).substring(2, 8);   // same-ms edits must not collide
const key = `${edit.fileUri}:${edit.timestamp}:${uniqueSuffix}`;
prevEditLruCache.set(key, edit);
```
```ts
// processNextEditData.ts — history FORGET + store-rich
let prevEdits: prevEdit[] = getPrevEditsDescending();   // most → least recent
if (prevEdits.length > 0) {
  if (timestamp - prevEdits[0].timestamp >= 1000 * 60 * 10 || workspaceDir !== prevEdits[0].workspaceUri) {
    prevEditLruCache.clear();                            // 10-minute staleness OR workspace switch ⇒ amnesia
    prevEdits = [];
  }
  filenamesAndDiffs = prevEdits.map(({fileUri, unidiff}) => ({
    filename: fileUri.replace(edit.workspaceUri, "").replace(/^[/\\]/, ""),
    diff: edit.unidiff.split("\n").slice(4).join("\n"),  // drop the 4-line unified-diff header for logging
  }));
}
...
const thisEdit: prevEdit = { unidiff: createDiff({..., contextLines: 25 /* storing many context lines for downstream trimming */}), ... };
setPrevEdit(thisEdit);
```

**Flow:** on each accepted edit: fetch descending history → forget-all if the newest entry is ≥10 minutes old or from a different workspace → log `nextEditWithHistory` telemetry ONLY when history was non-empty → create THIS edit's diff with `contextLines: 25` and push into the LRU.
**Invariant:** Store RICH (25-line context diffs), trim DOWNSTREAM — downstream consumers re-trim to their experiment's budget rather than losing hunk context at capture time. The random key suffix makes same-millisecond edits distinct entries instead of overwrites. History is a per-session in-memory ledger (no persistence) and its unit of validity is "same workspace AND <10 min".
**Probe:** deterministic source pins: `grep -n 'maxPrevEdits\|1000 \* 60 \* 10' core/nextEdit/context/prevEditLruCache.ts core/nextEdit/context/processNextEditData.ts`; consumer pin `processSmallEdit.ts:40-52` (`void processNextEditData(...)` fire-and-forget). Coverage caveat: no dedicated direct test at this pin.
**Note (experiment residue):** `processNextEditData` hardcodes `modelName = "Codestral"` / `modelProvider = "mistral"` and `maxPromptTokens = randomNumberBetween(500, 12000)` with the real config path commented out — porters must treat these as experiment scaffolding, NOT defaults to adopt.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "continue", query: "prevEditLruCache setPrevEdit getPrevEditsDescending", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the bounded ledger shape (≤5, timestamp+workspace forget ladder, random-keyed entries, rich-store/trim-downstream); adapt size/staleness windows; omit the hardcoded Codestrol-era experiment constants. No direct test — pinned by decisive source ranges.

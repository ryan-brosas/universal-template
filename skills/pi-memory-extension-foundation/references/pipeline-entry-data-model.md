<!-- capsule-v2 -->
# Pipeline entry data model — what unit flows through scan → merge → budget, and why does it carry content twice?

**Source:** pi-memory-extension MIT `main@f3b4377f46d75e49a8dda65d0408aab70d669839`; Codebase Memory `pi-memory-extension`. **Question:** A porter must decide the shape of the record flowing through the memory pipeline — getting `content` vs `injected` wrong breaks both truncation accounting and observability.

## The three interfaces (`MemoryFileEntry` :39–48, `MemoryCache` :50–56, `MemoryConfig` :11–24)
**Path/Symbol:** `pi-memory.ts:MemoryFileEntry` (:39–48), `pi-memory.ts:MemoryCache` (:50–56); config counterpart `MemoryConfig`/`DEFAULT_CONFIG` (:11–33, contract covered by init-idempotence-phantom-config).
**Signature:** pure data interfaces, no methods.
**Data Shape:** entry = `{ relPath: string; content: string; injected: string; source: "global" | "workspace" }`; cache = `{ globalRoot: string; workspaceRoot: string | null; files: MemoryFileEntry[]; stateContent: string }`.

### Decisive source
```ts
interface MemoryFileEntry {
  /** Path relative to memory root (e.g. "user/preferences.md") */
  relPath: string;
  /** Raw content */
  content: string;
  /** Truncated content used for injection */
  injected: string;
  /** Source layer */
  source: "global" | "workspace";
}

interface MemoryCache {
  globalRoot: string;
  workspaceRoot: string | null;
  files: MemoryFileEntry[];
  /** state/current-task.md content, loaded separately */
  stateContent: string;
}
```

**Flow:** `loadLayer` builds entries with BOTH copies at read time (`injected: truncateContent(raw, config.maxFileChars)`) → merge reorders whole entries without recomputation → `buildMemoryBlock` renders only `f.injected` into sections → `/memory:status` prints the PAIR `(f.injected.length)/(f.content.length) chars` making truncation visible per file.
**Invariant:** Carrying raw and truncated side-by-side is what lets truncation be a ONE-TIME decision at load instead of being recomputed per render, AND what keeps observability honest after truncation happened. Consequences to preserve: (1) `mergeLayers` overrides by basename regardless of either layer's truncation — an overriding workspace file replaces the global entry INCLUDING its already-truncated body; (2) `source` is the single field driving merge precedence, section routing in buildMemoryBlock, and status `[G]/[W]` tags — one field, three consumers that must stay consistent; (3) state lives OUTSIDE `files[]` as a separate trimmed string, so budget logic can treat it as always-keep; (4) `workspaceRoot: null` is the machine-readable "layer not opted in" signal mirroring the sentinel check. Graph fan-in confirms these are the pipeline's hubs: `MemoryFileEntry` and `MemoryConfig` each resolve with in-degree 3.
**Probe:** No upstream test suite exists. Pass-4 executed retrieve (GREEN): BM25 `"MemoryFileEntry injected raw content source layer cache"` ranks both interfaces in the top 4 (`MemoryCache` :50–56 rank-1 group tail, `MemoryFileEntry` :39–48 rank-3) alongside their two biggest consumers (`truncateContent`, `loadLayer`) — the graph itself exposes the data-model/consumer adjacency. Byte-level confirmation via direct read of :35–60 this pass; dual-copy behavior cross-checked against cited loadLayer/status ranges (:119–137, :291–315).
**Coverage caveat:** no upstream suite; interface facts pinned by direct read + live retrieves at pin.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-memory-extension", label: "Interface", limit: 10, fields: ["lines"] });
```
(Executed pass 4: total=3 — MemoryCache 50-56, MemoryConfig 11-24, MemoryFileEntry 39-48; has_more=false.)

## Verdict
Adopt the dual-content entry (raw + render-ready copy + layer tag) for any prompt-budgeted file store: it buys deferred rendering decisions, honest observability, and merge-without-recompute. Adapt field names to host vocabulary; keep `source` as the single precedence discriminator and keep volatile state out of the knowledge list. Omit nothing silently — collapsing `injected` into a render-time computation is a legitimate redesign but changes status reporting and merge semantics together. Coverage caveat: pinned by executed retrieves + byte-cited ranges (no upstream suite).

<!-- capsule-v2 -->
# Compress/decompress contract — how does message-range compression keep an addressable trail while restoration defaults to zero context growth?

**Source:** billion-context-pi (MIT) `master@558a83a9db69`; Codebase Memory project `billion-context-pi`. **Question:** What addressing, accounting, and restoration defaults must a port reproduce so compression stays reversible without polluting context?

## mNNNNN refs + partial-success batches + file-first restore + path jail
**Path/Symbol:** `src/compress-tool.ts` (126L) → thin wrapper over kernel `applyCompression`; `src/decompress-tool.ts` (213L): dual addressing (:155-160), `findMessageContent` (:99-109), path jail (:67-80), size defaults.
**Signature:** compress `{content: [{topic?, startId, endId, summary}]}` — refs are message ids (`"m00005"`) or block ids (`"b3"`); decompress `{blockId | messageId, inline?, full?, toFile?}`.
**Data Shape:** blocks store ONLY summary + ref sets; original text lives in the append-only session log (`findMessageContent` scans `sessionManager.getEntries()`); state persisted as `<session>.acp.json`.

### Decisive source
```ts
// decompress-tool.ts:67-80 — toFile paths jailed by relative() containment:
// allowed roots = /tmp, ~/.cache/opencode, ~/.cache/pi. Anything resolving
// outside is rejected ("decompress toFile rejects paths outside allowed roots").
// Size-appropriate defaults (:77-109):
//   block  → auto-file ~/.cache/pi/acp-decompress/b5-<ts>.txt (timestamped so
//            repeats never overwrite) + 600-char head preview
//   message→ inline when < MESSAGE_INLINE_THRESHOLD (2000 chars), else file
// The block STAYS compressed — restore-to-file never touches live context or
// disrupts the prompt-cache prefix; inline:true is explicit opt-in to cost.
```

**Flow:** compress validates each range then delegates to the kernel engine; batched ranges report PER-RANGE errors/warnings — PARTIAL SUCCESS, one bad range never aborts the batch. Token accounting measures LIVE uncovered context only: `estimateTokens` skips messages emitted by the compress tool itself AND every id in active blocks' `effectiveMessageIds`; result line `▣ ACP | 12.3K → 4.5K tokens (~7.8K reclaimed, 2 blocks)`; debug events record every span. Message-ref resolution happens BEFORE block-id because pure-digit hex UUIDs would misparse as block numbers (:155-160).
**Invariant:** (1) compression keeps an addressable trail — refs + summaries + covered-id sets — so any byte is locatable later. (2) Restoration grows context only by explicit choice (file-first with previews; `full:true` recurses nested tiers down to originals). (3) Source of truth for original content is the append-only log, NOT the compressed layer. (4) Model-written summaries preserve paths/signatures/errors verbatim and never cover content the current step is using.
**Probe:** `tests/decompress-tool.test.ts:77-129`: default writes auto-file (:77), inline returns content (:94), toFile honored (:104), outside-roots rejection (:117), block stays active after file-mode call (:124).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "billion-context-pi", query: "makeCompressTool makeDecompressTool findMessageContent", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the trail + file-first-restore + per-range partial success wholesale. Adapt cache paths/thresholds to your platform. Omit the kernel's tier engine internals (imported dependency, separate concern).

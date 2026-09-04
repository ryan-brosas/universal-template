<!-- capsule-v2 -->
# Compressed-only search index — which messages belong in context search, and who owns a message folded into multiple blocks?

**Source:** billion-context-pi (MIT) `master@6a88c5565355baebccfaf27398a6008fe08619ed`; Codebase Memory project `mnt-hdd-utopia-inspo-billion-context-pi`. **Question:** How do you build a search corpus over compressed history without re-indexing messages the model can still see?

## Index ONLY block-covered messages; earliest block wins ownership; never trust the host's visibility
**Path/Symbol:** `src/search-index.ts`: `buildSearchDocs` (:58-94), `buildCoveredRefs` (:24-30), `buildMessageOwnerMap` (:32-41), local `estimateTokens` (:43-48).
**Signature:** `buildSearchDocs(ctx, state) -> SearchDoc[]` = `[...blockDocs(state), ...messageDocs(msgs)]` (kernel helpers).
**Data Shape:** SearchDoc kinds `block | message`; message docs carry `{ref, role, text, tokens, blockId, tier}`.

### Decisive source
```ts
// search-index.ts:13-15 — the visibility-source-of-truth ruling:
// "We deliberately do NOT use pi's buildContextEntries for the visible check:
//  ACP prunes messages itself (no pi `compaction` entry is written), so pi
//  reports ALL entries as in-context. The ACP state is the source of truth."
// :76-78 — inclusion predicate:
// Only include messages that were compressed into a block.
// Still-live messages are visible to the model — no need to search them.
if (!covered.has(cm.id)) continue;
```

**Flow:** union of every block's `effectiveMessageIds` (active AND inactive) = searchable set → owner map assigns each ref to its FIRST (earliest) covering block — "outermost summary" wins when nested tiers overlap → per-message CJK-aware token estimate (`cjk chars count 1:1 + others /4`) → concatenate block docs + message docs and hand to the kernel's keyword scorer. The search tool renders hits with ref, role, tier, score, size, preview, and the EXACT decompress command to run next (`decompress({blockId:"b3"})` or the owning block for a message hit).
**Invariant:** (1) visibility truth lives in YOUR compression state, not the host's session view — hosts unaware of your pruning report everything as visible. (2) Searching is framed as the cheap pre-step: "Use BEFORE decompressing to find the right block." (3) Owner = earliest block so decompressing one block recovers maximal surrounding detail.
**Probe:** `tests/tokens.test.ts:21-38` pins the covered-id skip + CJK-consistent estimator used by the indexer; `tests/decompress-tool.test.ts:77-129` pins the file/inline/toFile-jail behavior of the retrieval endpoint the hints point at. (Index assembly itself has no dedicated suite — kernel `searchBlocks` is exercised indirectly; caveat re-verified at this pin: no `tests/search-index*` or `tests/*search*` file exists, glob control healthy.)

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-billion-context-pi", query: "buildSearchDocs buildCoveredRefs buildMessageOwnerMap", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt covered-only indexing + earliest-block ownership whenever you prune context yourself. Adopt the results-render contract (each hit carries its next command). Adapt the token estimator to your tokenizer. Omit kernel scoring internals (imported, not reimplemented).

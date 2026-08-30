<!-- capsule-v2 -->
# Compress/decompress contract — how does message-range compression keep an addressable trail while restoration defaults to zero context growth?

**Source:** billion-context-pi (MIT) `master@6a88c5565355baebccfaf27398a6008fe08619ed`; Codebase Memory project `mnt-hdd-utopia-inspo-billion-context-pi`. **Question:** What addressing, accounting, and restoration defaults must a port reproduce so compression stays reversible without polluting context?

## mNNNNN refs + partial-success batches + file-first restore + hardened path jail
**Path/Symbol:** `src/compress-tool.ts` (259L): `makeCompressTool` (:41-66), lenient arg normalization `normalizeRanges` (:77-84, THROW on bad input :143-148), success/noop panel classifiers (:101-120), tier-3 rewrite rejection (:122-139, throw :200-204), `handleCompress` sent-view measurement (:141-258); `src/decompress-tool.ts` (279L): `makeDecompressTool` (:33-58), symlink-hardened path jail `resolveToFilePath` (:68-115), `findMessageContent` (:134-144), full-tree ref recovery `resolveBlockMessages` (:155-171), message-ref decompress `handleMessageRef` (:176-215), dual addressing in `handleDecompress` (:217-279; message-ref FIRST at :225).
**Signature:** compress `{content: [{topic?, startId, endId, summary}] | "<json-encoded array>"}` — refs are message ids (`"m00005"`) or block ids (`"b3"`); decompress `{blockId | messageId, inline?, full?, toFile?}`.
**Data Shape:** blocks store ONLY summary + ref sets; original text lives in the append-only session log (`findMessageContent` scans `sessionManager.getEntries()`); state persisted as `<session>.acp.json`.

### Decisive source
```ts
// compress-tool.ts:143-146 — argument errors THROW, never return:
// "pi-agent-core only sets isError:true on THROWN tool errors, and the retry
//  nudge keys off isError. A returned string would land as isError:false —
//  no nudge, and the counter resets."
if (typeof maybeRanges === "string") throw new Error(maybeRanges);

// decompress-tool.ts:221-231 — dual addressing, message-ref resolved FIRST
// ("pure-digit hex refs ... would otherwise be misread as a block number"):
const owner = state.blocks.find((b) => b.effectiveMessageIds.includes(arg));
if (owner) return handleMessageRef(arg, owner.blockId, args, ctx);
const blockId = parseBlockIdArg(arg);
```

**Flow:** compress normalizes each range through the kernel's lenient parser (fenced / trailing-comma / double-stringified forms — non-strict providers stringify array arguments), measures the calibrated sent view exactly like the transform (`estimateTokens` over uncovered messages + measured system prompt, then `calibrateTokens` ×density :151-162), delegates to the kernel engine, and re-measures AFTER compression through a second processTurn (:212-218) so `▣ ACP | X → Y (~Z reclaimed)` compares like-for-like including the new block's own summary. Batched ranges report PER-RANGE errors/warnings — PARTIAL SUCCESS. Decompress defaults blocks to file mode (`~/.cache/pi/acp-decompress/b5-<ts>.txt`, timestamped so repeats never overwrite) with a 600-char head preview, single messages to inline under MESSAGE_INLINE_THRESHOLD=2000 chars (:190); `full:true` recurses nested tiers; when the active branch lagged a tree navigation, `resolveBlockMessages` recovers refs from the FULL session tree via getEntry, normalizing `${entryId}#${callId}` base ids both sides.
**Invariant:** (1) compression keeps an addressable trail — refs + summaries + covered-id sets — so any byte is locatable later. (2) Restoration grows context only by explicit choice; the block STAYS compressed — restore-to-file never touches live context or disrupts the prompt-cache prefix. (3) Source of truth for original content is the append-only log, NOT the compressed layer. (4) Model-written summaries preserve paths/signatures/errors verbatim and never cover content the current step is using. (5) toFile paths are jailed by relative() containment against realpath'd allowed roots (/tmp, ~/.cache/opencode, ~/.cache/pi) WITH symlink resolution — longest-existing-ancestor walk plus dangling-link lstat/readlink re-resolution, so a link inside the jail cannot escape it (:68-115). (6) A 0-block panel is a FAILED attempt, not success — otherwise no-op compressions loop with the emergency nudge (issue #6).
**Probe:** `tests/decompress-tool.test.ts`: default writes auto-file (:88), inline returns content (:105), toFile honored (:115), outside-roots rejection (:128), symlink escape rejected (:135), dangling symlink rejected (:150), block stays active after file-mode call (:162), getEntry fallback after undo (:174); `tests/compress-tool.test.ts`: density-1 beforeTokens (:62), density-calibrated beforeTokens (:82), like-for-like afterTokens/reclaimed (:119); `tests/t3-rewrite-guard.test.ts:77` (T3-only rewrite rejected + state rolled back).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-billion-context-pi", query: "makeCompressTool makeDecompressTool findMessageContent", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the trail + file-first-restore + per-range partial success wholesale, plus the two newer guards: classify tool outcomes by panel block count (success requires ≥1 block) and reject terminal-tier re-condensation explicitly rather than looping. Adapt cache paths/thresholds to your platform; keep the jail symlink-proof if users can write anywhere. Omit the kernel's tier engine internals (imported dependency, separate concern).

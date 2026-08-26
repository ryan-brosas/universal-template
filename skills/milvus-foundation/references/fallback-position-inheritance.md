<!-- capsule-v2 -->
# Compaction fallback positions & output position recalc — how do compacted segments inherit message-stream positions so incremental reads stay correct?

**Source:** Milvus Apache-2.0 `master@034e9fbba47aac1346caed8bf9df8d612297e5d7`; Codebase Memory `ext-milvus`. **Question:** When N input segments merge into M outputs, where do the new segments' StartPosition/DmlPosition come from?

## getCompactionFallbackPositions + recalculateSegmentPosition
**Path/Symbol:** `internal/datacoord/meta.go:completeMixCompactionMutation` position block (lines 2586–2611); helpers `getCompactionFallbackPositions` / `recalculateSegmentPosition` (same file, defined above 2541).
**Signature:** `startPos, dmlPos := recalculateSegmentPosition(compactToSegment.GetInsertLogs(), t.GetChannel(), fallbackStart, fallbackDml)`.
**Data Shape:** `*msgpb.MsgPosition{ChannelName, Timestamp}`; fallbacks computed once from ALL compactFrom infos; per-output override derived from the output's OWN insert logs.

### Decisive source
```go
fallbackStart, fallbackDml := getCompactionFallbackPositions(compactFromSegInfos)
...
for _, compactToSegment := range result.GetSegments() {
    startPos, dmlPos := recalculateSegmentPosition(
        compactToSegment.GetInsertLogs(), t.GetChannel(), fallbackStart, fallbackDml)
    ...
    StartPosition: startPos,
    DmlPosition:   dmlPos,
```

**Flow:** Before iterating worker results, the merger computes channel-wide fallback positions = earliest start / latest dml across all inputs. For EACH output segment it tries to recover true positions by scanning that segment's own insert-log entries (the compactor stamps per-record timestamps); missing/unreadable ⇒ fall back to the shared pair. The resulting proto then carries these as its checkpoint identity toward the streaming system.
**Invariant:** A merged segment's dmlPosition must never move BACKWARD past any retained delete/insert it now physically contains, and never forward past data still owned by sibling outputs — deriving per-output from own logs with input-wide fallback is what keeps both properties without cross-output negotiation. Zero-row outputs get Dropped anyway, so their inherited positions are inert.
**Probe:** Direct-source pin: call site :2586/:2590. Upstream coverage: mix task suites assert plan/result plumbing (`compaction_task_mix_test.go:74 TestBuildCompactionRequest_MixFileResources`); position helper itself is exercised through CompleteCompactionMutation paths in meta tests.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-milvus", query: "recalculateSegmentPosition getCompactionFallbackPositions", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt derive-then-fallback position inheritance for log-structured merges feeding incremental consumers. Adapt MsgPosition to your checkpoint primitive. Omit milvus channel re-stamping detail. Caveat: cgo-blocked runner; direct source read at pin.

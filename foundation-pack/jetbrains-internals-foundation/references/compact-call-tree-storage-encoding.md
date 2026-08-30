<!-- capsule-v2 -->
# Compact call-tree encoding — how do you store millions of stack frames so reads stay flat, concurrent, and diff-safe?

**Source:** JetBrains dotTrace standalone distribution (proprietary distribution; study/reference use only, citations-only), pin `?@?` (not git-managed; identity = root + generation 2026-08-24T13:55:36Z); Codebase Memory `jetbrains-dottrace` (12,537 nodes, FULL mode). **Question:** Which pointer encoding + traversal order makes a huge call tree cheap to persist and safe to read concurrently — and what breaks tree-diff arithmetic?

## First-child/next-sibling with last-child back-pointer
**Path/Symbol:** `JetBrains.Common.CallTreeStorage.xml`: `CompactTreeNode.Reference`, `BinaryReaderCompactTreeReader`, `IIndexableCompactTreeReader`, `Dfs.IEmittedDfsNodeConsumer{3}.{Start,End}NodeProcessing`, `Dfs.KeyToNodesAscendingIndex{3}`; diff guard in `JetBrains.Common.Timeline.EventLog.Interface.xml`: `SubtractResult.IsValid`.
**Signature:** `Reference: node-id // "Sibling or parent(if last child)"`; `StartNodeProcessing(oldIndex,newIndex,leftIndex,key)`; `EndNodeProcessing(oldIndex,newIndex,DfsNode{K,N})`.
**Data Shape:** one reference field per node encodes next-sibling OR (for a last child) the parent — three roles, one slot; DFS post-order emission assigns dense 0..n indices; index tables store keys ascending.

### Decisive source
```text
CompactTreeNode.Reference: "Sibling or parent(if last child)"
StartNodeProcessing: "called immediately after node index is assigned. newIndex values
    come sequentially from 0..n. No information about parent index is available."
IIndexableCompactTreeReader: "work with IStructuredMemory. All pointers translated
    to 0-based indices."
BinaryReaderCompactTreeReader: "Used for multithread access to the tree stored in stream…
    allows reuse of BinaryReaders"
SubtractResult.IsValid: "must be checked before using Diff value… offsets from different
    call tree groups cannot be subtracted… fall back to reading data via batch readers
    to skip inner nodes."
```

**Flow:** build via DFS post-order emitter → Start hook runs BEFORE the parent index exists (consumers must defer parent linkage to End) → serialized tree uses the single-reference encoding so upward walks reuse the same slot → readers either translate pointers to 0-based indices over structured memory or share stream BinaryReaders across threads → tree-vs-tree subtraction returns per-node results flagged `IsValid`; invalid nodes force batch-reader fallback instead of wrong numbers.
**Invariant:** one-slot tri-role reference keeps nodes at fixed minimal width; sequential index assignment is a hard ordering contract; cross-group offset subtraction is FORBIDDEN — validity flags are part of the result type, not an afterthought.
**Probe:** deterministic content assertions: grep the Reference summary and SubtractResult.IsValid summary by line number in their respective XML planes (recorded in verification.md).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-dottrace",
  query: "MemoryMappedStorage CallTreeStorage", limit: 5 });
// → jetbrains-dottrace.JetBrains.Common.CallTreeStorage.doc @ JetBrains.Common.CallTreeStorage.xml
//   (verified live); member-level text is not indexed — read the cited member summaries directly.
```

## Verdict
Adopt the single-slot sibling-or-parent encoding + dense post-order indexing + validity-flagged diffs for any large hierarchical aggregate. Adapt node payload/key types. Omit the ETW/timeline capture side that produces these trees.

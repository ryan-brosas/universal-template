<!-- capsule-v2 -->
# Mark-after-filter memory dedup — why must readFileState writes wait until after the duplicate filter runs?

**Source:** locoagent (Claude Code CLI fork, rev `c01bb3f`); Codebase Memory `locoagent`. **Question:** the ordering that prevents a dedup cache from self-referentially dropping everything.

## filterDuplicateMemoryAttachments
**Path/Symbol:** `src/utils/attachments.ts:filterDuplicateMemoryAttachments` (:2506-2541).
**Signature:** `(attachments: Attachment[], readFileState: FileStateCache) → Attachment[]` — mutates readFileState as a documented side effect.
**Data Shape:** operates only on `relevant_memories` members; passes all other types through untouched; drops the whole attachment when zero memories survive.

### Decisive source
```ts
/**
 * The mark-after-filter ordering is load-bearing: readMemoriesForSurfacing
 * used to write to readFileState during the prefetch, which meant the filter
 * saw every prefetch-selected path as "already in context" and dropped them
 * all (self-referential filter). Deferring the write to here, after the
 * filter runs, breaks that cycle while still deduping against tool calls
 * from any iteration.
 */
return attachments.map(attachment => {
  if (attachment.type !== 'relevant_memories') return attachment
  const filtered = attachment.memories.filter(m => !readFileState.has(m.path))
  for (const m of filtered) {
    readFileState.set(m.path, { content: m.content, timestamp: m.mtimeMs,
                                offset: undefined, limit: m.limit })
  }
  return filtered.length > 0 ? { ...attachment, memories: filtered } : null
}).filter((a): a is Attachment => a !== null)
```

**Flow:** consume point (`query.ts:1604`) awaits the settled prefetch → this fn filters memories whose paths the model already has via FileRead/Write/Edit (any iteration — readFileState is cumulative) → survivors are THEN written into readFileState so subsequent turns never re-surface them → emptied attachments removed entirely.
**Invariant:** any cache used both as dedup-source and dedup-marked-target must be written strictly AFTER reading/filtering, or the first pass poisons every later pass. Writes carry `limit` (truncation line count) so downstream change detection can skip partial views, and `offset/limit: undefined` otherwise so mid-session edit detection keeps working.
**Probe:** no upstream test (coverage caveat); regression rationale pinned verbatim :2506-2519. Deterministic probe: order check via `sed -n '2520,2541p' src/utils/attachments.ts` — `.filter(...has)` precedes the `readFileState.set` loop.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "filterDuplicateMemoryAttachments readFileState mark after filter", limit: 5, fields: ["signature","name","file"] });
```

## Verdict
Adopt mark-after-filter for any read/dedup/mark cache cycle; adapt cache type; omit attachment-type specifics. Porting trap: marking inside the producer (the historical bug) makes the selector surface nothing forever after the first turn — a silent total loss that looks like "memories stopped being relevant".

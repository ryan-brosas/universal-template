<!-- capsule-v2 -->
# Record content cap — truncate the RECORD, never the SOURCE; provenance stays whole by construction

**Source:** pi-observational-memory MIT `master@1a50dcd4eff2f2a2f298706499aa7096806d51d4`; Codebase Memory `pi-observational-memory`. **Question:** When an LLM worker emits a memory record with unbounded content, where do you clamp — and what must you never clamp?

## The cap (`src/serialize.ts`)
**Path/Symbol:** `serialize.ts:102` (`MAX_RECORD_CONTENT_CHARS = 10_000`), `serialize.ts:104-109` (`truncateRecordContent`).
**Signature:** `truncateRecordContent(content: string): string`.
**Data Shape:** threshold on JS `.length` (UTF-16 code units, not bytes); appended marker carries the exact dropped count.

### Decisive source
```ts
export const MAX_RECORD_CONTENT_CHARS = 10_000;

export function truncateRecordContent(content: string): string {
	if (content.length <= MAX_RECORD_CONTENT_CHARS) return content;
	const head = content.slice(0, MAX_RECORD_CONTENT_CHARS);
	const dropped = content.length - MAX_RECORD_CONTENT_CHARS;
	return `${head} … [truncated ${dropped} chars]`;
}
```

**Flow (both consumers):** observer tool handler (`agents/observer/agent.ts:126`) clamps every incoming observation before `hashId(content)` and ledger storage; reflector normalization (`agents/reflector/agent.ts:102`) clamps reflection content BEFORE its validator runs. So a record's id is always the hash of exactly what gets stored.

**Invariant:** This is a RECORD-side cap only. The SOURCE side has its own budget machinery (`source-addressed-serialization.md`: head/tail excerpt under the observer input budget) and the raw ledger entry is NEVER modified — recall can always recover the full original by id. Clamping at the record boundary means: bounded model context per memory line forever after, while provenance remains complete by construction. The marker text `[truncated N chars]` is part of the stored content, so the hash covers the truncation too — two records truncating differently get different ids, no silent collision. Porters who instead cap source serialization AND record content identically lose the "raw evidence stays recallable" property that the whole id-recall system depends on.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-observational-memory", query: "truncateRecordContent MAX_RECORD_CONTENT_CHARS runObserver normalizeReflectionContent hashId", limit: 10 });
```
(Direct tests: below unit granularity as a standalone contract — pinned to `serialize.ts:104-109` plus both consumer call sites `observer/agent.ts:126`, `reflector/agent.ts:102`; the observer suite exercises the handler path containing it.)

## Verdict
Adopt the single record-side clamp applied pre-hash at BOTH worker boundaries, the honest dropped-count marker, and the strict record-cap vs source-budget separation. Adapt the 10k threshold to your context economics. Omit nothing behavioral.

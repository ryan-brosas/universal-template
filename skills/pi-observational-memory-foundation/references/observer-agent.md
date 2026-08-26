<!-- capsule-v2 -->
# Observer agent — tool-collected batches with allowlist validation and progress receipts

**Source:** pi-observational-memory MIT `master@1a50dcd4eff2f2a2f298706499aa7096806d51d4`; Codebase Memory `pi-observational-memory`. **Question:** How do you get an LLM to compress a conversation chunk into provenance-backed records without hallucinated citations?

## Tool-as-collector (`src/agents/observer/agent.ts`)
**Path/Symbol:** `agent.ts:101-230` (`runObserver`), `agent.ts:84-99` (`normalizeSourceEntryIds`), `agent.ts:108-158` (`record_observations` tool).
**Signature:** `runObserver(args): Promise<Observation[] | undefined>` — `undefined` = clean empty; throws `ObserverStreamError` on stream failure.
**Data Shape:** schema forces `timestamp` (pattern `^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}$`), single-line `content` (minLength 1), enum `relevance`, non-empty `sourceEntryIds`.

### Decisive source
```ts
const sourceEntryIds = normalizeSourceEntryIds(obs.sourceEntryIds, allowedSourceEntryIds);
if (!sourceEntryIds) { rejected++; continue; }        // any unknown id ⇒ WHOLE observation rejected
```
```ts
export function normalizeSourceEntryIds(sourceEntryIds, allowedSourceEntryIds): string[] | undefined {
	if (!sourceEntryIds || sourceEntryIds.length === 0) return undefined;
	const allowedOrder = new Map(...);
	for (const id of sourceEntryIds) {
		if (!allowedOrder.has(id)) return undefined;      // one bad id poisons the batch item
		seen.add(id);
	}
	// re-emit in CHUNK order (allowedOrder index), not model order
	return Array.from(seen).sort((a, b) => (allowedOrder.get(a) ?? 0) - (allowedOrder.get(b) ?? 0));
}
```
```ts
const ack = `Recorded ${added} new observation(s)... Total so far this run: ${accumulated.size}. Continue if the chunk still has uncovered content; otherwise stop calling the tool...`;
return { content: [{ type: "text", text: ack }], details: { added, duplicates, rejected, total: accumulated.size } };
```

**Flow:** user message carries current reflections + observations as dedupe context, the labeled chunk, current local time → loop runs; each `record_observations` call validates ids against the serializer's allowlist (reject-all-on-any-unknown), dedupes by content hash, truncates >10k-char content, accumulates into a Map → the TOOL REPLY is a progress receipt telling the model what's left → run ends when the model stops calling and emits plain text.
**Invariant:** The model cannot invent provenance: ids outside the chunk are rejected atomically per observation, and accepted id arrays are re-sorted to chunk order so records are deterministic. Duplicates by content-hash are counted, not stored. Empty accumulated set + stream error ⇒ throw; empty + clean stop ⇒ `undefined` (deliberate empty). `maxTokens` clamps to the model's own cap via `boundedMaxTokens`; optional `maxTurns` gates via `shouldStopAfterTurn`.

## Prompt contract essentials (`src/agents/observer/prompts.ts`)
**Data Shape:** system prompt frames "these records are the ONLY memory after compaction" + emission rules.

### Decisive source
```
Preserve user assertions exactly. ... Assertions are authoritative — a later question on the same topic does not invalidate them.
  BAD:  User wondered if they have two kids.
  GOOD: User stated they have two kids.
Frame state changes as supersession so the old state is explicit.
  GOOD: User will use React Query (switching from SWR).
Observations with missing, empty, or invalid sourceEntryIds will be rejected and not recorded...
```

**Flow:** prompt teaches assertion-vs-question framing, exact-quote preservation of unusual terms, precise action verbs, supersession framing, grouping repeated tool calls, and skip-routine-events permission ("fine to emit zero").
**Invariant:** Prompt rules mirror validator behavior exactly (rejection warning ↔ `normalizeSourceEntryIds` returning `undefined`) — a mismatch between promised and actual rejection semantics is the classic porting bug.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-observational-memory", query: "runObserver normalizeSourceEntryIds record_observations ObserverStreamError RecordObservationsSchema", limit: 10 });
```
(Direct tests: `tests/observer.test.ts` pins acceptance/rejection/dedupe; `tests/stream-errors.test.ts` pins error-vs-empty.)

## Verdict
Adopt tool-call accumulation with progress receipts, atomic per-record allowlist rejection, chunk-order normalization, content-hash dedupe, and the strict clean-empty vs stream-failure split. Adapt schema field names/thinking level defaults. Omit pi-agent-core specifics (`streamSimple`, `AgentLoopConfig`) in favor of your host's loop equivalent.

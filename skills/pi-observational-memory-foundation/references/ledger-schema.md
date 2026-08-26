<!-- capsule-v2 -->
# Append-only memory ledger schema — typed custom entries, content-hash ids, validate-then-build

**Source:** pi-observational-memory MIT `master@1a50dcd4eff2f2a2f298706499aa7096806d51d4`; Codebase Memory `pi-observational-memory`. **Question:** How do you record agent-generated "memory" inside a session ledger you don't own, so it survives replay and can never corrupt the host session?

## Entry taxonomy (`src/session-ledger/types.ts`)
**Path/Symbol:** `types.ts:1-67` (constants + shapes), `types.ts:93-152` (validators), `types.ts:178-200` (builders).
**Signature:** three custom entries appended via `pi.appendEntry(customType, data)`:
`om.observations.recorded { observations[], coversUpToId }`, `om.reflections.recorded { reflections[], coversUpToId }`, `om.observations.dropped { observationIds[], coversUpToId }`.
**Data Shape:** `Observation = { id(12-hex), content(single-line), timestamp("YYYY-MM-DD HH:MM" local), relevance(low|medium|high|critical), sourceEntryIds[](host branch-entry ids), tokenCount }`; `Reflection = { id, content(no \r|\n), supportingObservationIds[] , tokenCount }`.

### Decisive source
```ts
export const MEMORY_ID_PATTERN = /^[a-f0-9]{12}$/;
// ids.ts
export function hashId(content: string): string {
	return createHash("sha256").update(content).digest("hex").slice(0, 12);
}
```
```ts
export function isObservationsRecordedData(value: unknown): value is ObservationsRecordedEntryData {
	if (!isPlainRecord(value)) return false;
	return (
		Array.isArray(value.observations) && value.observations.length > 0 &&
		value.observations.every(isObservation) && isNonEmptyString(value.coversUpToId)
	);
}
export function buildObservationsRecordedData(observations, coversUpToId) {
	if (observations.length === 0 || !isNonEmptyString(coversUpToId)) return undefined;
	return { observations, coversUpToId };
}
```

**Flow:** worker agents produce candidate records → per-record validation (`isMemoryId`, single-line reflection content, non-empty source arrays, finite non-negative token counts) → builder returns `undefined` for empty sets → caller skips appending when `undefined`.
**Invariant:** The extension NEVER mutates host entries; all memory lives in `type:"custom"` entries it owns. Every recorded batch carries `coversUpToId` = a SOURCE branch-entry id (the coverage anchor), not a memory-entry id. Ids are content hashes (sha256[:12]), which gives dedupe-for-free: identical content ⇒ same id ⇒ duplicates collapse everywhere. Validators are re-run at every read (fold/projection/recall), so hand-edited or truncated ledgers degrade gracefully instead of throwing.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-observational-memory", query: "Observation Reflection MEMORY_ID_PATTERN isObservation buildObservationsRecordedData hashId", limit: 10 });
```
(`types.ts` fully indexed, coverage `no_recorded_issue`; direct tests `tests/session-ledger-types.test.ts` pin validator behavior incl. V2 rejection.)

## Verdict
Adopt the append-only custom-entry pattern, content-hash 12-char hex ids, `coversUpToId` as a source-entry anchor, validate-at-read defensive parsing, and builders that return `undefined` rather than empty records. Adapt custom-type names, relevance vocabulary, and the 4-chars/token estimate to your host. Omit nothing behavioral; note that reflection content forbids newlines BY VALIDATOR, not just by prompt.

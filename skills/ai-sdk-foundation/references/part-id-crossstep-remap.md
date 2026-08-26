<!-- capsule-v2 -->
# Cross-step part-id remap — how do provider content-block ids stay unique across a multi-step stream?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f2243035491e9de5a2e00ebf9eb17`; Codebase Memory `ai`. **Question:** Providers assign text/reasoning part ids per model call (Anthropic's block index restarts at 0 every call) — how does the merged multi-step stream keep them collision-free without breaking delta/end correlation?

## First-wins reserver with suffix ladder
**Path/Symbol:** `packages/ai/src/generate-text/stream-text.ts:createPartIdReserver` (:1167–1187), instances `reserveTextPartId`/`reserveReasoningPartId` (:1189–1190); applied in the step-stream merge transform (:2275–2325).
**Signature:** `(id: string) => string` — closure over one `Set<string>` of used ids.
**Data Shape:** Per STEP, `const textPartIds = new Map<string,string>()` maps provider id → emitted id for that step's deltas/ends.

### Decisive source
```ts
return (id: string) => {
  if (!usedIds.has(id)) { usedIds.add(id); return id; }
  const generatedId = generateId();
  let uniqueId = generatedId, suffix = 0;
  while (usedIds.has(uniqueId)) uniqueId = `${generatedId}-${++suffix}`;
  usedIds.add(uniqueId);
  return uniqueId;
};
// start: const id = reserveTextPartId(chunk.id);
//        textPartIds.set(chunk.id, id); enqueue({...chunk, id});
// delta/end: enqueue({...chunk, id: textPartIds.get(chunk.id) ?? chunk.id});
// end additionally: textPartIds.delete(chunk.id);
```

**Flow:** first occurrence of an id passes through unchanged; any later collision remaps start/delta/end consistently THROUGH THE PER-STEP MAP so the triple stays correlated under a new id; map entries die at their `-end`. Separately, empty text-deltas with no providerMetadata are dropped entirely (consumers must not materialize zero-width parts).
**Invariant:** Within the merged logical stream, no two concurrently-open text (or reasoning) parts share an id, and every delta/end carries exactly the id its start was assigned this step. The reserver Set spans steps; the correlation Map is per-step by design.
**Probe:** `stream-text.test.ts:15913/:16031` — "the first provider ID is kept, the collision is remapped"; deterministic probe: `grep -c createPartIdReserver packages/ai/src/generate-text/stream-text.ts` → `3` (factory + two instances).
**Retrieve caveat:** `createPartIdReserver` is a closure-local const and graph-invisible by construction — anchor retrieval on `reserveTextPartId` usage or read the source range directly; do not treat total:0 as absence.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "text-start remap duplicate part ids", limit: 10, fields: ["signature", "name", "file"] });
// fallback anchor (closure-local symbol): grep pins above; live battery confirmed streamObject/streamText ranges nearby
```

## Verdict
Adopt first-occurrence-wins with generated-id suffix ladder and per-step correlation maps; adapt the id generator; omit the empty-delta drop only if your reducer tolerates zero-width parts. Porters who trust provider ids across steps will corrupt UI state keyed by part id.

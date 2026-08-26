<!-- capsule-v2 -->
# Trace-to-memory ingestion — how do nested fabric executions become independently searchable memory entries without polluting the outer transcript?

**Source:** pi-fabric MIT `feat/veda-runner@4874ac3abefab27ee0064a3c8571ee017ceb3115`; Codebase Memory `pi-fabric`. **Question:** what does the audit→memory bridge emit, and how do structural filters stay exact?

## Typed event fan-out + operation-address expansion
**Path/Symbol:** `src/compaction/trace-events.ts` (imports from `../audit`; feeds compaction normalize), consumed by `src/memory/normalize.ts` (fabricOperation entries carry `{index, entryId, address, tool, ref, provider?, action?, args, outcome, error?, result?}`); projection-side join mirrored in `collectOperations` (`src/compaction/projections.ts:118`).
**Signature:** each nested op becomes its OWN normalized entry with a distinct `address`, emitted AFTER the outer entry in transcript order; filters match on exact fields: role/toolName/ref/provider/action/outcome/timestamps.
**Data Shape:** `address` = stable per-operation retrieval key (distinct from the outer tool call's entryId) — this is what `[entry <address>]` lines and digest 10-tuples point at.

### Decisive source
```ts
// trace-events.ts: audit operations become typed compaction events
if (event.kind === "fabricOperation") {
  operations.push({ index: event.index, entryId: event.entryId, address: event.address,
    tool: event.tool, ref: event.ref,
    ...(event.provider ? { provider: event.provider } : {}),
    ...(event.action ? { action: event.action } : {}),
    args: event.args, outcome: event.outcome,
    ...(event.error !== undefined ? { error: event.error } : {}),
    ...(event.result !== undefined ? { result: event.result } : {}),
    nested: true });
}
```
```ts
// search.ts: cold digests filter on the SAME tuple grammar — positions fixed
if (filters.provider !== undefined && address[7] !== filters.provider) return false;
if (filters.action   !== undefined && address[8] !== filters.action)   return false;
if (filters.outcome  !== undefined && address[9] !== filters.outcome)  return false;
```

**Flow:** an execution's sealed V1 trace (audit-trace-envelope) is projected into typed events → normalizers append one entry PER nested operation after the outer fabric_exec result → memory indexing treats them like any entry (BM25 over text + exact structural fields) → searches can select `provider=X action=Y outcome=failed` exactly; segment rendering can expand an outer hit by operation-address to show the specific nested op.
**Invariant:** children are searchable INDEPENDENTLY of the parent ("emits independently searchable children after the outer entry with exact structural fields") while the outer transcript keeps a single fabric_exec line (compaction-projection-folds suppression rule); malformed/unknown trace versions are IGNORED at this boundary instead of being adapted into audits — version skew degrades to absence, never to wrong data.
**Probe:** `tests/memory-trace-integration.test.ts:68` ("emits independently searchable children after the outer entry with exact structural fields"), `:96` ("supports tool filters, operation-address expansion, and cold vocabulary"), `:251` ("ignores malformed and unknown trace versions instead of adapting audits").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "trace-events fabricOperation address outcome provider action normalizeSession addresses", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt one-entry-per-nested-op fan-out with stable operation addresses and strict-version ingestion gating; adapt the field tuple to your trace schema; omit the fabric ref vocabulary. Direct integration tests cited; graph coverage clean.

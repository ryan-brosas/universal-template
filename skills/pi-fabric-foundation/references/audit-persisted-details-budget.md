<!-- capsule-v2 -->
# Persisted-details budget + legacy render bridge — how do you shrink an already-built trace for storage and still render old transcripts?

**Source:** pi-fabric MIT `feat/veda-runner@4874ac3abefab27ee0064a3c8571ee017ceb3115`; Codebase Memory `pi-fabric`. **Question:** what lands in final tool details, and how does rendering stay backward-compatible with pre-trace audit blobs?

## Aggregate-bound persisted object + legacy-wins reader
**Path/Symbol:** `src/audit/details.ts:createFabricPersistedExecutionDetails` (:53-90), `readFabricExecutionRenderDetails` (:131-170), `auditFromOperation` (:114-124), `legacyAudit` (:95-112).
**Signature:** `createFabricPersistedExecutionDetails({success, trace, outputFormat?, outputFormatStartLine?, outputFormatLines?}): FabricPersistedExecutionDetailsV1`; `readFabricExecutionRenderDetails(value: unknown): FabricExecutionRenderDetails`.
**Data Shape:** persisted = `{success, trace (structuredClone'd), outputFormat?, outputFormatStartLine?≥0 floor, outputFormatLines?}` bound as a WHOLE to 512 KiB (`FABRIC_EXECUTION_DETAILS_MAX_BYTES`). Rich per-call audits are deliberately NOT copied into details.

### Decisive source
```ts
// The aggregate object, not each member independently, is bound.
while (serializedBytes(details) > FABRIC_EXECUTION_DETAILS_MAX_BYTES && details.trace.operations.length > 0) {
  details.trace.operations.pop();
  details.trace.counts.droppedOperations++;      // every shrink is counted
}
while (serializedBytes(details) > MAX && details.trace.phases.length > 0) { …pop(); droppedValues++ }
if (serializedBytes(details) > MAX) { delete details.trace.error; counts.droppedValues++; }
```
```ts
// Legacy audits win when present so old transcripts retain their historical rich previews.
audits: oldAudits ?? trace?.operations.map(auditFromOperation) ?? [],
phases: oldPhases ?? trace?.phases ?? [],
```

**Flow:** clone the trace (caller's object never mutated) → pop operations, then phases, then the run error until the AGGREGATE serializes ≤ limit, bumping `counts` each time → on read, validate `value.trace` through `isFabricExecutionTraceV1`; if legacy `audits` array exists it takes precedence over trace-derived audits; `success`/`error` resolve from explicit fields first, then from `trace.outcome === "succeeded"` / `trace.error`. Trace-derived render audits map action→tool and collapse outcome to a boolean.
**Invariant:** storage shrink mutates only the CLONE and always increments counters (honesty preserved through a second budget layer); readers accept BOTH generations forever — you cannot render a mixed corpus without a dual-shape reader; malformed traces degrade to empty `{audits:[], phases:[]}`, never throw.
**Probe:** `tests/audit-trace.test.ts:996` (details envelope bound asserted alongside trace bound), `:89` ("records successful calls … and preserves legacy audits"), `:771` ("reconstructs current render audits from trace and preserves legacy audit rendering").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "createFabricPersistedExecutionDetails readFabricExecutionRenderDetails FabricLegacyRenderAudit droppedOperations", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt aggregate-bound shrinking with counted drops and the legacy-wins dual reader; adapt the extra fields (outputFormat window lines) to your renderer; omit the fabric-specific field names. Direct tests cited; graph coverage clean.

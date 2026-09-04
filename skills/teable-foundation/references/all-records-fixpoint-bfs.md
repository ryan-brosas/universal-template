<!-- capsule-v2 -->
# ALL_RECORDS growth fixpoint — how do conditional filters, link cascades, and re-closures iterate to a stable impact set?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** When does the record-impact loop terminate and why is re-running the whole link closure safe?

## collect() work-loop
**Path/Symbol:** `apps/nestjs-backend/src/features/record/computed/services/computed-dependency-collector.service.ts:collect` (:1650–1783; twin loop in `collectForFieldChanges` :1269–1399).
**Signature:** internal; mutates `explicitSeeds: Map<tableId, Set<recordId>>` + `tablesWithAllRecords: Set<tableId>` until no growth.

### Decisive source
```ts
// :355–358 growth detector
if (prevSet === ALL_RECORDS && nextSet !== ALL_RECORDS) {
  // This should not happen; treat as unchanged.
  continue;
}
// :1691–1699 materialize ONLY when a concrete-target edge needs it
if (rawSet === ALL_RECORDS) {
  const needsMaterialization = referenceEdges.some((edge) => {
    const targetSet = recordSets[edge.tableId];
    return targetSet !== ALL_RECORDS && edge.tableId !== src;
  });
  shouldMaterializeAllRecords = needsMaterialization;
```

**Flow:** queue seeded from initial closure growth; each pop filters conditional edges to those whose TARGET field is in the impact set (twice-checked :1676–1679 and again after await :1746); matched ids either mark a table ALL_RECORDS (`markAllSeed` sets `preferAutoNumberPaging=true`) or join `explicitSeeds`; ANY dirty result triggers a FULL `computeLinkClosure` re-run (:1766–1780) and re-enqueues grown tables plus their link dependents. Sentinel semantics are one-way ratchets: Set→ALL allowed, ALL→Set treated as unchanged.
**Invariant:** Sets only GROW across iterations (monotone) so re-running the resolver cannot lose previously-discovered ids and the loop terminates. Re-enqueue on EVERY dirty table (not just the popped one) because junction re-walk may reach tables through new paths. The eager ALL short-circuit (:1717–1724) skips SQL when the source saturates AND every target is already saturated or IS the source.
**Probe:** needle verified at this pin (`treat as unchanged.` :357); behavior pinned by `packages/v2/e2e/src/computed-high-cardinality-link.e2e.spec.ts` (multi-hop convergence); graph retrieval `findRecordSetGrowth` resolves :334–377.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "computeLinkClosure", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt monotone-growth fixpoint with full re-closure on dirty; adapt the ALL sentinel to an enum in languages without Symbols; omit the duplicated loop body by extracting it (upstream keeps two copies).

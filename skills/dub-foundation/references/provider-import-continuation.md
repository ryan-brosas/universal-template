<!-- capsule-v2 -->
# Importer continuation engine — how do five near-identical provider importers page through upstream APIs under a batch ceiling, and what is the resume + completion protocol?

**Source:** dub AGPL-3.0-or-later `main@e3a558d1cf5d`; Codebase Memory project `dub`. **Question:** How does an import survive serverless time limits across QStash invocations, and when do provider credentials get deleted?

## toltImporter class + importCommissions while-loop: MAX_BATCHES → self-requeue → credentials teardown
**Path/Symbol:** `apps/web/lib/tolt/importer.ts:ToltImporter` (:10-58); loop `apps/web/lib/tolt/import-commissions.ts:importCommissions` (:22-124); per-row creator `createCommission` (:131-360); scheduled-commission twin `apps/web/lib/partnerstack/import-scheduled-commissions.ts` (:12-100+); same pattern in firstpromoter/rewardful/tapfiliate importers.
**Signature:** `while (hasMore && processedBatches < MAX_BATCHES)` with `startingAfter` cursor threaded through the payload; MAX_BATCHES=5, CACHE_EXPIRY=24h, Redis credential key `tolt:import:${workspaceId}`.
**Data Shape:** payload `{importId, programId, <providerProgramId>, userId, startingAfter?}`; status map `toDubStatus: pending→pending, approved→pending, paid→paid, rejected→canceled, refunded→refunded` (:14-20).

### Decisive source
```ts
await new Promise((resolve) => setTimeout(resolve, 2000));      // politeness gap between pages
startingAfter = commissions[commissions.length - 1].id;
processedBatches++;
}
if (hasMore) {
  await toltImporter.queue({ ...payload, startingAfter, action: "import-commissions" });  // self-requeue
  return;
}
await toltImporter.deleteCredentials(program.workspaceId);       // ONLY on full completion
...
await toltImporter.queue({ ...payload, startingAfter: undefined, action: "update-stripe-customers" });
```
(:96-123)
```ts
const trackedCommission = await prisma.commission.findFirst({
  where: { programId, createdAt: { gte: new Date(chargedAt - 60*60*1000), lte: new Date(chargedAt + 60*60*1000) },
           customerId, type: "sale", amount: saleAmount } });
if (trackedCommission) return;   // already recorded live during the migration transition window
```
(:246-263)

**Flow:** credentials fetched from Redis (throw if expired mid-import — 24h TTL bounds total import duration) → each invocation processes ≤5 upstream pages: fetch page → bulk-load matching customers (+their Tinybird lead events) ONCE per batch → allSettled per-row creators → 2s sleep → advance cursor → ceiling hit ⇒ re-enqueue SELF with the advanced cursor (content-based dedup off) and exit; exhausted ⇒ delete the stored provider credentials, email the importer a ProgramImported summary with error stats, then chain the NEXT action (`update-stripe-customers`) via the queue. Per row: transaction_id required → `(invoiceId,programId)` dedup → customer/link/click/partner/lead-event ladder of typed logImportError rows → FX-convert sale+earnings to USD from cached `fxRates:usd` → ±1h same-customer-same-amount transition-window dedup → create commission + recordSaleWithTimestamp + link/customer stat updates keyed on isFirstConversion.
**Invariant:** (1) progress lives ENTIRELY in the re-enqueued payload's cursor — any invocation can die without corrupting state; (2) credentials are torn down only after the LAST page so an interrupted import never loses auth mid-stream (and the 24h TTL silently kills zombie imports); (3) every skip reason becomes a queryable import-error row (Tinybird), not a silent continue; (4) the ±1h fuzzy dedup protects against double-counting rows that dub's own live tracking recorded before the switch-over.
**Probe:** deterministic probe: `grep -n 'MAX_BATCHES = 5' apps/web/lib/tolt/importer.ts` = :8; `grep -c 'deleteCredentials' apps/web/lib/tolt/import-commissions.ts` = 1. No upstream unit suite covers the importers (recorded caveat).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "importCommissions", limit: 8 });
```

## Verdict
Adopt the cursor-in-payload self-requeue loop with batch ceilings, terminal credential teardown, and action-chaining for any long-running third-party migration. Adapt provider clients/status maps. Omit the transition-window heuristic if your import starts from an empty ledger.

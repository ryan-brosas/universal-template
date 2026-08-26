<!-- capsule-v2 -->
# Payout export split — when does a CSV export become a background job, and how do both paths share column semantics?

**Source:** dub AGPL-3.0-or-later `main@e3a558d1cf5d`; Codebase Memory project `dub`. **Question:** What are the two export paths' thresholds and guarantees (sync inline vs async R2 + email), and how does the worker cap memory?

## payouts/export route + cron/export/payouts + async generator
**Path/Symbol:** sync `apps/web/app/(ee)/api/payouts/export/route.ts:GET` (:11-59); async `apps/web/app/(ee)/api/cron/export/payouts/route.ts:POST` (:20-100); paging generator `apps/web/app/(ee)/api/cron/export/payouts/fetch-payouts-batch.ts:fetchPayoutsBatch` (:10-40); storage `apps/web/lib/api/create-downloadable-export.ts:13-52`.
**Signature:** sync: count > MAX_PAYOUTS_TO_EXPORT(1000) ⇒ QStash publish + **202** `{}`; else stream CSV with `Content-Disposition: attachment`. Async: page 1000 at a time, hard cap MAX_PAYOUTS_EXPORT_LIMIT=100k via `formatted.slice(0, remaining)`.
**Data Shape:** job body carries `columns: columns.join(",")` stringified; worker re-parses filters through payoutsQuerySchema minus pagination; download link = 7-day signed R2 URL.

### Decisive source
```ts
if (count > MAX_PAYOUTS_TO_EXPORT) {
  await qstash.publishJSON({ url: `.../api/cron/export/payouts`,
    body: { ...filters, columns: columns.join(","), workspaceId, programId, userId } });
  return NextResponse.json({}, { status: 202 });
}
```
(sync :26-39)
```ts
const remaining = MAX_PAYOUTS_EXPORT_LIMIT - allRows.length;
if (remaining <= 0) break;
allRows.push(...formatted.slice(0, remaining));
```
(async :73-79)

**Flow:** both paths format rows through the SAME formatPayoutsForExport(columns) so spreadsheets match regardless of size → async accumulates rows in memory up to 100k (bounded by slice against remaining budget), converts to CSV once, uploads to private R2 with content-disposition metadata, emails an ExportReady template with the signed URL.
**Invariant:** (1) 202-with-empty-body is the contract the UI polls on — never 200; (2) the cap trims the LAST batch rather than failing, trading completeness for guaranteed delivery; (3) signed URLs expire in 7 days — exports are ephemeral, not archival.
**Probe:** deterministic probe: `grep -n 'status: 202' 'apps/web/app/(ee)/api/payouts/export/route.ts'` = :38; `grep -n 'MAX_PAYOUTS_EXPORT_LIMIT = 100_000' 'apps/web/app/(ee)/api/cron/export/payouts/route.ts'` = :17. No upstream unit suite covers these routes directly (recorded caveat).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "createDownloadableExport", limit: 5 });
```

## Verdict
Adopt the count-gated sync/async split and remaining-budget trimming. Adapt limits/storage. Omit nothing else in this seam.

<!-- capsule-v2 -->
# Source
NocoDB `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73` — `packages/nocodb/src/dbQueryClient/cross-db-utils/applyAggregation.ts` :76–84 — Barcode/QR unwrap.

# Question
How do virtual display columns (Barcode, QrCode) aggregate their underlying value while keeping the REQUESTED column's identity?

## Path / Symbol
Barcode/QrCode swap block in applyAggregation.

## Signature
```ts
if (column.uidt === UITypes.Barcode || column.uidt === UITypes.QrCode) {
  column = new Column({
    ...(await column.getColOptions<BarcodeColumn | QrCodeColumn>(context)
      .then(col => col.getValueColumn(context))),
    id: column.id,        // <-- requested column's id wins
  });
}
```

## Data Shape
The swapped Column carries the VALUE column's colOptions/uidt (so later typed-branch logic sees e.g. Number) but the BARCODE column's id (so aliases/result keys still match what the caller asked for).

## Decisive source
applyAggregation.ts:77–84 — the spread order is the contract: value-column fields first, `id: column.id` LAST so it overrides. Without the override, result keys would name an invisible helper column and the UI couldn't attach the stat to the barcode cell.
This runs BEFORE getColumnNameQuery (:95) so the SQL expression resolves against the value column — barcodes have no physical storage; QR/barcode columns are pure projections.
Note the asymmetry with Formula: formulas KEEP their own uidt through compilation (parsedFormulaType drives typed branches instead), because formula columns already carry a compiled expression; barcode/QR need full substitution.

## Flow / Invariant
Porter rule for virtual-column stats: separate IDENTITY from SUBSTANCE — aggregate the substance (value column), report under the identity (requested id). The `{...substance, id: identity}` spread idiom encodes both in one line and should survive any port verbatim.

## Probe (direct test)
From repo root:
```
grep -n 'id: column.id' packages/nocodb/src/dbQueryClient/cross-db-utils/applyAggregation.ts   # => 1 (:82)
grep -c 'getValueColumn' packages/nocodb/src/dbQueryClient/cross-db-utils/applyAggregation.ts                    # => 1 (:81)
```

## Retrieve
```
codebase-memory-mcp cli search_graph '{"project":"mnt-hdd-utopia-inspo-platforms-nocodb","query":"Barcode QrCode getValueColumn","limit":2,"detail":"compact"}'
```
→ resolves the swap block line-exact.

## Verdict
**Adopt.** Identity/substance split with the last-spread-id idiom ports directly to any projected-column analytics.

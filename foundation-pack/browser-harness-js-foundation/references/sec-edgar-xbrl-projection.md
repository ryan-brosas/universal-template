<!-- capsule-v2 -->
# SEC EDGAR XBRL Projection — candidate concepts, recency-wins, dedup, sign normalization

## Source
Repo: browser-harness-js @ main`6b18940` (unchanged vs base_sha).

## Question
How does findata turn the multi-MB `companyfacts` XBRL blob into a clean income/balance/cashflow statement table?

## Path / Symbol
`skills/findata/scripts/findata` :239-262 (projection expr array joined into one in-page IIFE); SKILL.md "Statement fields" + "Traps" sections document the same contract for users.

## Signature
```js
// Per FIELD a CANDIDATE LIST of US-GAAP concepts, preferred order first:
revenue: ["RevenueFromContractWithCustomerExcludingAssessedTax","Revenues","SalesRevenueNet"]
capex:   ["PaymentsToAcquirePropertyPlantAndEquipment","PaymentsToAcquireProductiveAssets"]
// pickField: concept whose MOST RECENT period (max f.end) is latest wins — so a stale legacy
// concept (e.g. Revenues after switching to RevenueFromContract...) never shadows the current one.
// periodOk: annual ⇒ fp==='FY'; quarterly ⇒ fp∈{Q1..Q4}; dim-allocated facts skipped.
// Dedup by period_end preferring the EARLIEST-filed 10-K fact:
function valForEnd(arr,end){ ... if (arr[i].form === wantForm) return arr[i]; if (!best) best = arr[i]; }
// Sign normalization (cashflow only): OUTFLOW = {capex,dividends_paid,share_repurchases,
// debt_repayment} → always negative regardless of filer convention; net subtotals keep as-reported signs.
// Derived: free_cash_flow = operating_cf + capex (capex normalized negative) = ocf − |capex| either way.
```

## Data Shape
`{ticker,name,cik,period,statement,statements:[{period_end,fiscal_year,fiscal_period,form,filed,accession,filing_url,...line items}]}` — every row traceable to the originating filing via accession + filing_url.

## Decisive source
SKILL.md Traps section (mirrors code exactly): quarterly facts are **YTD cumulative** as-reported ("a Q3 figure is the 9-month cumulative") and are NOT differenced; duplicate period_end facts arise from comparative restatements ("same end, same value, later one tagged with a frame like CY2024") and earliest-10-K preference points each column at the ORIGINAL filing; share-class tickers normalize `.`→`-` (BRK.B → BRK-B) because both SEC's company_tickers.json and Yahoo key with hyphens. Ticker→CIK map cached on `globalThis.__secTickerMap` (:227-236). The projection runs inside the navAndPoll readiness poll so "the (multi-MB) body is parsed exactly once, when ready" (:140-142).

## Flow / Invariant
1. Candidate-list-per-field + latest-period-wins resolves filer concept drift without per-company config.
2. period_end dedup must prefer earliest 10-K or columns silently point at restatements instead of originals.
3. Only the four known-outflow line items get sign-normalized; net subtotals stay as-reported (normalizing them would flip real outflows into inflows).
4. Coverage caveat stays honest: a field shows `-` when the filer uses a concept outside the candidate list (e.g. Apple reports dividends under PaymentsOfDividends).

## Probe (direct tests)
No upstream unit tests; smoke harness `bash skills/findata/scripts/test` runs live calls against SEC/Yahoo. Deterministic probes at pin: `grep -c "RevenueFromContractWithCustomerExcludingAssessedTax" skills/findata/scripts/findata` → 2; `grep -c "OUTFLOW" skills/findata/scripts/findata` → 2; `grep -c "padStart(10" skills/findata/scripts/findata` → 1 (CIK zero-padding to CIK0000320193 form).

## Retrieve
grep-first (`pickField`, `MAPS`, `valForEnd`).

## Verdict
ADOPT the whole XBRL-to-statement pipeline; the recency-wins rule and earliest-filing dedup are the two invariants that keep financial output trustworthy.

<!-- capsule-v2 -->
# Sheets header retrofit guard — how do you guarantee a shared output sheet has a header row without ever overwriting existing data rows?

**Source:** hassan-sales-nav-profiles-scraper (no LICENSE file in tree — pattern-only) `main@e294ac09c9b9`; Codebase Memory `hassan-sales-nav-profiles-scraper` (coverage `no_recorded_issue`+`metadata_match`). **Question:** when several runs (or several destinations) share one spreadsheet, what is the decision trichotomy that retrofits a header row idempotently?

## empty-append vs nonempty-insert-at-1 vs already-headed no-op
**Path/Symbol:** `linkedin_scraper.py:main` (:136–143) — runs only inside the sheet-CHANGE branch, so it fires at most once per destination per run.
**Signature:** `worksheet.row_values(1) -> list[str]`; `worksheet.get_all_values() -> list[list[str]]`; `append_row(row)`; `insert_row(row, index=1)`.
**Data Shape:** header = `['Name', 'Profile-Link']` (matches the two-column append schema :216); sentinel = literal first-cell string `"Name"`.

### Decisive source
```python
# Ensure headers exist
first_row = worksheet.row_values(1)
if not first_row or first_row[0] != 'Name':
    if not worksheet.get_all_values():
        worksheet.append_row(['Name', 'Profile-Link'])      # truly EMPTY sheet → header at the end
    else:
        worksheet.insert_row(['Name', 'Profile-Link'], index=1)  # DATA PRESENT → push down, never overwrite
```

**Flow:** read row 1 → if absent OR its first cell is not the `"Name"` sentinel: ask whether the sheet has ANY values at all → empty ⇒ append header as row 1 of an empty grid; non-empty but unheaded ⇒ INSERT at index 1 so every existing data row shifts down intact; already headed ⇒ do nothing.
**Invariant:** existing data rows are NEVER overwritten or deleted — the only destructive-looking op (`insert_row`) pushes rows DOWN. The sentinel check makes re-entry idempotent: a second run on the same sheet takes the no-op branch because `first_row[0] == 'Name'`. The guard lives in the switch branch, not the page loop — O(1) API reads per destination switch, zero per page.
**Probe:** repo has no tests and Sheets needs live OAuth — coverage caveat recorded; claim source-grounded. Executed probes: `grep -n "row_values(1)\|get_all_values()\|insert_row" linkedin_scraper.py` ⇒ :138/:140/:143 exactly (single decisive block); `grep -n "append_row" linkedin_scraper.py` ⇒ exactly 5 call sites (:141 header-append inside THIS guard, :216 per-row data append, :231–:233 marker trio owned by in-sheet-page-set-marker).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "hassan-sales-nav-profiles-scraper", query: "main", limit: 3 });
// ⇒ rank#1 …linkedin_scraper.main :33–259 (executed: resolved rank#1). Name-only index — body keywords
// return 0 by construction; byte-exact greps (:138/:140/:143) are the standing source-read evidence.
```

## Verdict
Adopt the three-way trichotomy (empty→append, unheaded-nonempty→insert-at-1, headed→no-op) for ANY shared append-only sink — spreadsheets, CSVs, DB tables; adapt the sentinel string and column set to the host schema; omit nothing structural. Contrast: na-preserving-row-extraction keeps CSV schemas total by pre-initializing NA fields per ROW; this seam protects the SCHEMA ROW itself across shared-sheet reuse — row-level defaults and header-level retrofit compose cleanly.

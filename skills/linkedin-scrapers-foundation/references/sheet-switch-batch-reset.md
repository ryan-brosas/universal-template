<!-- capsule-v2 -->
# Sheet-switch batch reset — how does an operator rotate the output destination mid-run while batch accounting stays coherent?

**Source:** hassan-sales-nav-profiles-scraper (no LICENSE file in tree — pattern-only) `main@e294ac09c9b9`; Codebase Memory `hassan-sales-nav-profiles-scraper` (coverage `no_recorded_issue`+`metadata_match`). **Question:** when the destination may change every few pages, where must bookkeeping state reset so no page is ever attributed to two destinations?

## prompt-cadence gate + lazy open-on-change + atomic accounting reset
**Path/Symbol:** `linkedin_scraper.py:main` — state init (:86–89), cadence gate (:121), validated choice loop (:123–128), switch branch (:130–135); consumed by the marker flush (:229–235).
**Signature:** gate: `(page_num - 1) % 2 == 0 or current_sheet_choice is None`; switch test: `if choice != current_sheet_choice:`.
**Data Shape:** `current_sheet_choice: int | None` (None forces first prompt even mid-pair); `worksheet` handle cached per destination; `records_since_separator: int`; `pages_in_current_batch: set[int]` — both reset ONLY on switch and at marker flush; `sheet_ids: dict[int, str]` fixed {1..4}.

### Decisive source (condensed: invalid-choice reprompt line :128 omitted)
```python
if (page_num - 1) % 2 == 0 or current_sheet_choice is None:
    while True:
        choice = input("Which Google Sheet do you want to store data to? (1, 2, 3, or 4): ").strip()
        if choice in ['1', '2', '3', '4']: choice = int(choice); break
    if choice != current_sheet_choice:            # reopen ONLY on a real change
        sh = gc.open_by_key(sheet_ids[choice]); worksheet = sh.sheet1
        current_sheet_choice = choice
        records_since_separator = 0               # batch accounting resets ATOMICALLY with the switch
        pages_in_current_batch = set()
```

**Flow:** at each even-page boundary (pages travel in pairs) or on first entry, prompt until the answer validates → if the destination actually changed: lazily open the new spreadsheet, cache its first worksheet, and zero BOTH accumulators in the same branch → subsequent data rows append to the new destination and rebuild its page set from empty.
**Invariant:** the destination switch is the SINGLE reset point for batch accounting mid-run — rows written before the switch can never appear in the new destination's marker page-list, because that set was cleared in the same branch that swapped `worksheet`. The worksheet handle is cached: one `open_by_key` round-trip PER SWITCH, ZERO per page. The `None`-initialized choice makes the very first boundary prompt deterministically, regardless of starting parity. Prompt cadence (`(page_num-1) % 2 == 0`) fires at the START of each pair, so an operator keeps or changes the destination before any row of the pair is written.
**Probe:** repo has no tests — coverage caveat recorded (source-grounded; interactive gspread flow not reproducible offline). Executed probes: `grep -n "current_sheet_choice\|pages_in_current_batch\|records_since_separator" linkedin_scraper.py` ⇒ exactly :87–:89 (init), :121 (gate), :130/:133/:134/:135 (switch+reset), :220/:221 (accumulate), :229/:234/:235 (flush) — matching the ownership map above; `grep -n "% 2 == 0" linkedin_scraper.py` ⇒ :121 and :229 only (prompt cadence and flush cadence are the pair boundaries).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "hassan-sales-nav-profiles-scraper", query: "main", limit: 3 });
// ⇒ rank#1 …linkedin_scraper.main :33–259 (executed: resolved rank#1). Name-only index — body keywords
// return 0 by construction; the :87–:135 line-map grep is the standing source-read evidence.
```

## Verdict
Adopt lazy-handle-plus-reset-on-change for ANY swappable sink (file, table, queue): cache the connection, reopen only when the target identity changes, and clear all cross-target accumulators inside that same branch; adapt prompt cadence and validation vocabulary to host actions; omit hard-coded destination IDs. Contrast: pattern-filtered-cookie-jar keys persistence per ACCOUNT; this seam keys OUTPUT routing per operator decision — both avoid re-opening/rewriting state that has not changed.

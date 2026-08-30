<!-- capsule-v2 -->
# In-sheet page-set marker — where does the human-visible resume pointer live so the OUTPUT itself records which pages produced which rows?

**Source:** hassan-sales-nav-profiles-scraper (no LICENSE file in tree — pattern-only) `main@e294ac09c9b9` (README Output-Format section corroborates the marker text); Codebase Memory `hassan-sales-nav-profiles-scraper` (coverage `no_recorded_issue`+`metadata_match`). **Question:** how do you make a shared append-only destination self-describing — anyone reading it can tell exactly which search pages contributed rows and where the last run stopped?

## distinct-page set → sorted 3-row separator block flushed per pair
**Path/Symbol:** `linkedin_scraper.py:main` — accumulate (:220–221), flush gate + render (:229–235); state owned by sheet-switch-batch-reset (:86–89, :130–135).
**Signature:** accumulate: `pages_in_current_batch.add(page_num)` per appended row; gate: `if page_num % 2 == 0 and pages_in_current_batch:`; render: `", ".join(map(str, sorted(list(pages_in_current_batch))))`.
**Data Shape:** marker = three appended rows — literal 50-char `=` ruler (spelled out, not an expression), `🌟 LAST SCRAPE ENDED HERE (Pages: <sorted csv>) 🌟` in column A, ruler again; the set holds DISTINCT page numbers, so a page yielding N rows still contributes ONE entry.

### Decisive source
```python
# inside the per-row island: every written row attributes its page (:220-221)
records_since_separator += 1
pages_in_current_batch.add(page_num)
# after each page: flush only on even boundary AND only if something was recorded (:229-235)
if page_num % 2 == 0 and pages_in_current_batch:
    pages_str = ", ".join(map(str, sorted(list(pages_in_current_batch))))
    worksheet.append_row(["==================================================", "=================================================="])
    worksheet.append_row([f"🌟 LAST SCRAPE ENDED HERE (Pages: {pages_str}) 🌟", ""])
    worksheet.append_row(["==================================================", "=================================================="])
    records_since_separator = 0
    pages_in_current_batch.clear()
```

**Flow:** each successfully appended data row adds its page number to a SET (dedupe by construction) → when the page counter hits an even boundary AND at least one row was recorded since the last marker: emit ruler/marker/ruler with the DISTINCT SORTED page list, then clear the set → next pair starts accounting from empty.
**Invariant:** the ledger lives IN the data destination — resume state cannot drift from data because they are the same stream. Flush requires non-empty accumulation: a timed-out or empty page leaves NO marker, so markers never claim work that produced nothing. `sorted()` makes the rendered list deterministic regardless of set iteration order. Sheet switches mid-pair stay correct because the switch branch clears the set before any new-destination row is added. Honest note: `records_since_separator` (:88/:134/:220/:234) is incremented and reset but NEVER READ anywhere — a vestigial counter; port the SET + marker block, not the dead integer.
**Probe:** repo has no tests — coverage caveat recorded (source-grounded). Executed probes: `grep -n "LAST SCRAPE ENDED HERE" linkedin_scraper.py` ⇒ :232 exactly; `grep -n "% 2 == 0" linkedin_scraper.py` ⇒ :121/:229 (prompt cadence and flush cadence share the pair boundary); README §Output-Format shows the identical 3-row block as the documented contract.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "hassan-sales-nav-profiles-scraper", query: "main", limit: 3 });
// ⇒ rank#1 …linkedin_scraper.main :33–259 (executed: resolved rank#1). Name-only index — string literals
// are not nodes; `grep -n "LAST SCRAPE ENDED HERE"` (:232) stands in as source-read evidence.
```

## Verdict
Adopt co-locating the human resume marker with the data rows, distinct-set attribution, sorted deterministic rendering, and the empty-page-no-marker rule; adapt marker vocabulary and cadence (pairs here, batches elsewhere) to host rhythm; omit the dead counter and the emoji if the host console lacks a utf-8 guard. Contrast: session-summary-ledger-append splits summary vs machine ledger across two writers in ONE file; durable-named-cursor-continuation encodes a MACHINE-resumable cursor — this seam is the third point of the triangle: a HUMAN-resumable cursor rendered into the data itself.

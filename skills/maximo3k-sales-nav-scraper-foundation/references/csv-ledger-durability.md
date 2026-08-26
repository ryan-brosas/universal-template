<!-- capsule-v2 -->
# CSV ledger durability — one write call per page, append-only, no dedup: crash loses exactly the current page

**Source:** maximo3k-sales-nav-scraper (license file, `main@bdcd2e5197929f78631ab127d2fd10cee18807ca`); Codebase Memory `maximo3k-sales-nav-scraper`. **Question:** What does the run guarantee about the CSV when a page or the whole run dies midway — what survives a crash and can rows repeat?

## Page-batched append-only ledger
**Path/Symbol:** `prospect_scraper_sales_navigator.py` — `write_results_to_csv(results, 'prospects_1.csv')` called from `scroll_extract` :120; the writer itself is :22–29.
**Signature:** `write_results_to_csv(results, filename)` — one call per page with the WHOLE page's rows as one list; the file handle opens in `'a'` mode per call.
**Data Shape:** the `results` list is created fresh at the top of every `scroll_extract` call (:58) and holds exactly one five-field dict per card on the current page. Nothing else touches the file during the page.

### Decisive source
```python
    # end of scroll_extract — after the for loop over all cards:
    write_results_to_csv(results, 'prospects_1.csv')
```
```python
def write_results_to_csv(results, filename):
    with open(filename, 'a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        if file.tell() == 0:
            writer.writerow([...header...])
        for result in results:
            writer.writerow([result['person_name'], ...])
```

**Flow:** extract every card of the current page into memory → ONE bulk append of that page's rows → click Next → repeat. The commit unit is therefore the PAGE: a crash (or Ctrl-C, which the author's usage comment :18 explicitly contemplates) during extraction of page N loses only page N's unflushed buffer — every earlier page was already appended and closed.
**Invariant:** the ledger is append-only across pages — no rewrite, no read-back, no dedup key exists anywhere in the file. Consequences a porter must accept or fix explicitly: (1) re-running the script on the same saved search APPENDS a full duplicate copy of every row under a fresh header-less continuation (the header guard only suppresses headers, never rows); (2) LinkedIn pagination overlap or an aborted-and-restarted run silently duplicates people. The empty tracked seed file `prospects_1.csv` proves the append target is expected to pre-exist or be created by the first write.
**Probe:** no test files exist in the repo — source-grounded evidence only (coverage caveat). Observable boundary: `write_results_to_csv` has exactly one call site (:120) inside the per-page function, not the per-page loop body; module scope (:159–164) contains no second flush.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "maximo3k-sales-nav-scraper", query: "write_results_to_csv append prospects_1.csv", limit: 10, fields: ["signature", "name", "file"] });
```
→ resolves the writer symbol (`prospect_scraper_sales_navigator.py` :22–29).

## Verdict
Adopt page-batch-as-commit-unit for crash-bounded loss, and treat the CSV as an append-only ledger where duplicates are the caller's problem. Adapt the batch size to the host (a smaller batch shrinks crash loss but multiplies header-guard checks). Omit nothing structural here — but if the host needs idempotent re-runs, ADD a dedup pass upstream; do not assume this contract provides one. No-test caveat applies.

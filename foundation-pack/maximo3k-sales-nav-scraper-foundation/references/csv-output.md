<!-- capsule-v2 -->
# CSV output — append five-field rows and write the header only on first write

**Source:** maximo3k-sales-nav-scraper (license file) `main@bdcd2e5197929f78631ab127d2fd10cee18807ca`; Codebase Memory `maximo3k-sales-nav-scraper`. **Question:** How does a scraper append result rows to a CSV across pages without repeating the header on every write?

## Header-on-first-write CSV append
**Path/Symbol:** `prospect_scraper_sales_navigator.py:write_results_to_csv` (22–29).
**Signature:** `def write_results_to_csv(results, filename) -> None`.
**Data Shape:** `results` is a list of dicts each with `person_name`, `person_title`, `person_company`, `person_location`, `person_link`; `filename` is a CSV path opened in append mode (`'a'`) with `newline=''` and UTF-8; the header is written only when the file cursor is at position 0.

### Decisive source
```python
def write_results_to_csv(results, filename):
    with open(filename, 'a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        if file.tell() == 0:
            writer.writerow(['person_name', 'person_title', 'person_company', 'person_location', 'person_link'])
        for result in results:
            writer.writerow([result['person_name'], result['person_title'],
                             result['person_company'], result['person_location'],
                             result['person_link']])
```

**Flow:** open the file in append mode -> if the file cursor is at 0 (empty/absent file) write the header row -> write one row per result dict.
**Invariant:** the header appears exactly once — only when the file was empty at open; append mode preserves rows already written by earlier pages.
**Probe:** no test file exists in the repo — this is source-grounded evidence only (coverage caveat).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "maximo3k-sales-nav-scraper", query: "write_results_to_csv csv.writer file.tell header", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the append-mode CSV writer with the `file.tell() == 0` header-on-first-write guard and UTF-8/`newline=''` handling. Adapt the output filename and field list to the host. Omit the hard-coded `prospects_1.csv` path unless a target needs it.

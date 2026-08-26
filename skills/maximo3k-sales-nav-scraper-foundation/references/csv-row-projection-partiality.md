<!-- capsule-v2 -->
# Row-projection partiality — direct five-key indexing makes schema violations latent tier-C crashes, and an exception persists the page prefix while process death loses it

**Source:** maximo3k-sales-nav-scraper (GPL-3.0 license file) `main@bdcd2e5197929f78631ab127d2fd10cee18807ca`; Codebase Memory `maximo3k-sales-nav-scraper`. **Question:** What happens to rows already written from the CURRENT page when the writer dies mid-page — and what breaks first if a producer's dict shape drifts?

## Direct-key row projection inside the page commit
**Path/Symbol:** `prospect_scraper_sales_navigator.py:write_results_to_csv` (`:22-29`, row loop `:28-29`).
**Signature:** `def write_results_to_csv(results, filename) -> None`; each row built by FIVE direct key reads: `result['person_name'] ... result['person_link']`.
**Data Shape:** a closed five-key schema produced at exactly two sites — the success append (:99-105) and the all-NA failure append (:112-118) — and consumed unconditionally here. Any producer omitting a key turns `write_results_to_csv` into a `KeyError` site.

### Decisive source
```python
    with open(filename, 'a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        if file.tell() == 0:
            writer.writerow(['person_name', 'person_title', 'person_company', 'person_location', 'person_link'])
        for result in results:
            writer.writerow([result['person_name'], result['person_title'], result['person_company'], result['person_location'], result['person_link']])
```

**Flow:** header (maybe) → per-row projection via direct indexing → `writer.writerow` into the buffered text stream → context-manager exit flushes on NORMAL unwind AND on exceptional unwind. The call site is `:120` inside `scroll_extract` OUTSIDE the card-tier try, so a writer exception propagates past `:135` (before the pagination try starts) out of module scope: tier C.
**Invariant:** partiality is FAILURE-MODE dependent. An IN-PROCESS exception after k data rows persists the header + those k rows (close-on-unwind flush — probe PROBE_B persisted 3 lines through a simulated mid-page RuntimeError), while process death loses the whole still-buffered page (that loss asymmetry is csv-ledger-durability's page commit unit). Meanwhile the closed schema means today's code can NEVER hit the KeyError — both producers always set all five keys — making direct indexing a LATENT crash that activates the moment any third producer or refactor drops a key (`KeyError: 'person_title'`, probe PROBE_A), killing the run at tier C with the window left open (no finally — see module-entry-no-main-guard).
**Probe:** executed pre-write (stdlib python3, exit 0): PROBE_A `carrier = {'person_name': 'x'}; carrier['person_title']` → `KeyError: 'person_title'`. PROBE_B buffered csv.writer inside a with-block writes header+2 rows then raises → file read-back after unwind = exactly `['person_name,person_title', 'ann,ceo', 'bob,cto']`. Probe replicates the writer-loop mechanics ('w' mode; append-vs-write mode does not affect buffering). Repo tests do not exist — source-grounded evidence only (coverage caveat).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "maximo3k-sales-nav-scraper", query: "write_results_to_csv results writer append", limit: 6 });
```
→ live-executed pre-write: total 3 → `write_results_to_csv` Function :22-29 (rank -17.07), `builtins.list.append`, `scrape_results_page` :124-153 — zero misses.

## Verdict
Adopt the closed-schema discipline: keep the field tuple in ONE place shared by every producer and the writer, or switch projection to `.get(..., 'NA')` if the host must tolerate drifting producers. Keep page batching (csv-ledger-durability) but document both partiality modes at the port site: exception ⇒ prefix survives, kill ⇒ page lost. Omit direct-index fragility wherever third parties can produce rows. No-test caveat applies.

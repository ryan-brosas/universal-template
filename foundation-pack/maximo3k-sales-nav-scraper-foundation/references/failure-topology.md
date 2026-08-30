<!-- capsule-v2 -->
# Failure topology — card errors degrade to NA rows, pagination errors end the run, login errors crash it

**Source:** maximo3k-sales-nav-scraper (license file, `main@bdcd2e5197929f78631ab127d2fd10cee18807ca`); Codebase Memory `maximo3k-sales-nav-scraper`. **Question:** Which failures does this scraper survive and which kill it — where are the try boundaries, and what happens at each one?

## Three-tier error containment
**Path/Symbol:** `prospect_scraper_sales_navigator.py` — tier A card loop `scroll_extract` try :67–110; tier B pagination `scrape_results_page` try :138–151; tier C uncaught module scope (:155–164).
**Signature:** two nested `try/except Exception` tiers inside an infinite `while True:` page loop; no try exists around login or config load.
**Data Shape:** tier A catches ANY exception per card and appends a pre-initialized all-`"NA"` row (:109–118), then continues the loop; tier B distinguishes `NoSuchElementException` (absent Next button = normal last-page exit, :146–148) from generic `Exception` (broken click = abort, :149–151) but both `break`; tier C has NO handler — `json.load(config.json)` (:155–156), `login_to_site` (:159), and the first `scrape_results_page` call (:160) propagate straight out of the module.

### Decisive source
```python
        except Exception as e:
            print(f"Failed to process item at index {index}: {str(e)}")
            # You may choose to append a record with NA values or just log the error
            results.append({
                'person_name': person_name,
                'person_title': person_title,
                'person_company': person_company,
                'person_location': person_location,
                'person_link': person_link,
            })
...
        except NoSuchElementException:
            print("No more pages to navigate.")
            break
        except Exception as e:
            print(f"Error navigating to next page: {str(e)}")
            break
```

**Flow:** per-card failure → log + all-NA row + NEXT CARD (run continues); per-page navigation failure after extraction → log + break (pages already extracted stay in the CSV); login/config failure → uncaught traceback, zero rows written. Note the containment is also NESTED: the re-find-by-index (`item = driver.find_elements(...)[index]`, :74) sits INSIDE the card-tier try, so even a mid-page DOM shift that breaks indexing only costs one NA row, never the page.
**Invariant:** degradation is strictly per-card and termination is strictly per-page — there is no retry anywhere, and the two `break` paths in tier B are deliberately equivalent exits (last page and error look identical from outside). The design accepts silently incomplete data over a crashed run: an all-NA row is the sentinel for "card failed here," so downstream consumers can filter by `person_name == 'NA'`.
**Probe:** no test files exist in the repo — source-grounded evidence only (coverage caveat). Observable boundary: the ONLY `except` clauses in the file are at :109 (card tier, bare `Exception`) and :146/:149 (pagination tier); lines :155–164 carry none.
**Coverage caveat:** because every handler is bare `Exception`, a porter cannot distinguish "LinkedIn redesigned the card" from "network died" from the logs alone — the printed message is the only signal.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "maximo3k-sales-nav-scraper", query: "scroll_extract except Exception scrape_results_page", limit: 10, fields: ["signature", "name", "file"] });
```
→ resolves both function carriers of the two try tiers (`scroll_extract` :57–122, `scrape_results_page` :124–153).

## Verdict
Adopt the tiered containment model: catch-per-unit at the innermost loop (degrade, don't die), break-not-retry at the outer loop, and let setup/auth failures crash loudly. Adapt the NA sentinel value and the log channel to the host. Omit the conflation of "absent button" and "button errored" into the same silent exit if the host needs to distinguish clean EOF from breakage. No-test caveat applies.

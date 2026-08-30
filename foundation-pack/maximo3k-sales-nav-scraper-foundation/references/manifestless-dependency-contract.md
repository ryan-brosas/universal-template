<!-- capsule-v2 -->
# Manifest-less dependency contract — the import block is the ONLY dependency declaration

**Source:** maximo3k-sales-nav-scraper (GPL-3.0 license file) `main@bdcd2e5197929f78631ab127d2fd10cee18807ca`; Codebase Memory `maximo3k-sales-nav-scraper`. **Question:** How does a porter reconstruct, pin, and audit this script's runtime dependencies when the repository ships no manifest at all?

## Import-census-only dependency surface
**Path/Symbol:** `prospect_scraper_sales_navigator.py` imports `:1-12` (module scope; graph node `maximo3k-sales-nav-scraper.prospect_scraper_sales_navigator` Module 1-164).
**Signature:** none — bare module-level statements carry no callable signature.
**Data Shape:** exactly 12 import lines = stdlib `csv`/`json`/`time` (:1/:2/:12) + 8 selenium names (:3-10: `webdriver`, `ChromeService`, `Options`, `By`, `Keys`, `WebDriverWait`, `EC`, `NoSuchElementException`) + 1 third-party helper (`webdriver_manager.chrome.ChromeDriverManager`, :11). No version pins exist anywhere.

### Decisive source
```python
import csv
import json
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options   # imported, NEVER used
...
from webdriver_manager.chrome import ChromeDriverManager
import time

driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()))  # :20 — network fetch of the driver binary
```

**Flow:** README step 1 says only "Install all the libraries necessary" → no requirements.txt / pyproject.toml / setup.py / setup.cfg / Pipfile / lockfile exists in the tree (probe P1) → a porter recovers the dependency set by reading :1-12 → installs unpinned `selenium` + `webdriver-manager` → at run start, `ChromeDriverManager().install()` (:20) downloads the chromedriver binary over the network BEFORE any browser work.
**Invariant:** the dependency surface IS the import block — nothing else constrains it. Two latent facts ride along: (1) `Options` (:5) is dead weight, evidence of an abandoned headless/options path — every run is headed Chrome; (2) the driver binary arrives via an unversioned network download at run time, so builds are not reproducible even with pinned pip packages.
**Probe:** executed pre-write against the pin (`git ls-files` = exactly README.md, config.json, license, prospect_scraper_sales_navigator.py, prospects_1.csv; six manifest globs all absent; `grep -cE '^(import|from)'` = 12). No test files exist in the repo — source-grounded evidence only (coverage caveat).

## Get live surrounding code
**Retrieve:** module-scope statements have no graph symbol (established pass 2); the query resolves the file's BM25 symbol carrier instead.
```ts
await mcp.codebase_memory.search_graph({ project: "maximo3k-sales-nav-scraper", query: "module imports csv json selenium webdriver", limit: 6 });
```
→ live-executed pre-write: total 1 → `prospect_scraper_sales_navigator.write_results_to_csv` Function :22-29 (rank -13.18), zero misses.

## Verdict
Adopt the recovery practice: treat a manifest-less script's import block as its dependency manifest and re-derive third-party vs stdlib before porting. Adapt by adding pins plus a driver-binary provisioning step (or vendor chromedriver management) for any reproducible host. Omit the unused `Options` import and the run-time network binary fetch when the host needs hermetic builds. No-test caveat applies.

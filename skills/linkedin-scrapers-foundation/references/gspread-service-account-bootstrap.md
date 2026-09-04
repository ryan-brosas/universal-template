<!-- capsule-v2 -->
# Sheets service-account bootstrap — how does a portable CLI locate its Google service-account key regardless of CWD and fail fast before any browser or network work?

**Source:** hassan-sales-nav-profiles-scraper (no LICENSE file in tree — README carries only a bare "MIT License" mention; treated pattern-only) `main@e294ac09c9b9`; Codebase Memory `hassan-sales-nav-project` N/A — project `hassan-sales-nav-profiles-scraper`, coverage `no_recorded_issue`+`metadata_match`. **Question:** where must a script resolve its credential file so it works from any launch directory, and what is checked before the expensive browser session starts?

## Script-relative key resolution + pre-flight existence gate
**Path/Symbol:** `linkedin_scraper.py:main` (:59–78) — scopes, `script_dir`/`creds_path` resolution, existence check, `Credentials.from_service_account_file` → `gspread.authorize`.
**Signature:** `Credentials.from_service_account_file(creds_path, scopes=scopes) -> gspread.authorize(credentials) -> gc`; later `gc.open_by_key(sheet_ids[choice])` lazily at first destination choice (:131).
**Data Shape:** `credentials.json` = Google service-account key (11 fields: type … universe_domain, per graph nodes); scopes = `["https://www.googleapis.com/auth/spreadsheets", "…/drive"]`; resolution anchor = `os.path.join(os.path.dirname(os.path.abspath(__file__)), "credentials.json")`.

### Decisive source
```python
# Get the directory where the script is located
script_dir = os.path.dirname(os.path.abspath(__file__))
creds_path = os.path.join(script_dir, "credentials.json")

if not os.path.exists(creds_path):
    print(f"❌ Error: credentials.json not found at {creds_path}")
    return                                   # abort BEFORE AdsPower/browser startup
credentials = Credentials.from_service_account_file(creds_path, scopes=scopes)
gc = gspread.authorize(credentials)
```

**Flow:** compute script-dir anchor → join key filename → existence probe with the RESOLVED ABSOLUTE PATH in the error message → build scoped credentials → authorize once → the authorized client sits idle until the operator picks a sheet and `open_by_key` runs.
**Invariant:** the lookup anchors to the SCRIPT's own directory (`__file__`-relative), never the process CWD, so launching from any shell finds the key; a missing key aborts the run before AdsPower startup — no half-started browser session can outlive a config failure. Authorization happens once per run; sheet OPENING stays lazy per destination switch.
**Probe:** repo has no tests — coverage caveat recorded (source-grounded). Executed probes: `grep -n "os.path.dirname(os.path.abspath(__file__))" linkedin_scraper.py` ⇒ exactly :67 (single decisive site); `grep -n "from_service_account_file\|gspread.authorize" linkedin_scraper.py` ⇒ :77/:78; `python3 -m py_compile linkedin_scraper.py` ⇒ exit 0.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "hassan-sales-nav-profiles-scraper", query: "main", limit: 3 });
// ⇒ rank#1 hassan-sales-nav-profiles-scraper.linkedin_scraper.main :33–259 — the seam's owning symbol
// (executed: resolved rank#1). This 47-node graph indexes SYMBOL NAMES only, not bodies — body-level
// keywords return 0 by construction; the byte-exact grep probes above stand in as source-read evidence.
```

## Verdict
Adopt `__file__`-anchored credential resolution + fail-fast existence check that names the absolute path it wanted, and lazy `open_by_key` per destination instead of eager opens; adapt scope pairs to the host API surface and the storage sink entirely; OMIT every credential artifact this repo commits (real `credentials.json` key, hard-coded AdsPower key :19, four hard-coded sheet IDs :80–85 — inject your own config). Contrast: sessions-json-cache persists LOGIN cookies per account; this seam bootstraps an API SERVICE ACCOUNT for the output sink — auth for writing results, not for scraping.

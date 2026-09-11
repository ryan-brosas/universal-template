<!-- capsule-v2 -->
# Logging & verbosity plane — how does one verbose knob retune eight per-site loggers, and why do display-name fixups exist?

**Source:** JobSpy MIT `main@fda080a373e8`; Codebase Memory `JobSpy`. **Question:** When must set_logger_level run so verbose actually reaches site loggers, and what keeps the finish-log on the right logger object?

## Namespaced loggers created at import, tuned at call time
**Path/Symbol:** `jobspy/util.py:create_logger` (:19–29), `jobspy/util.py:set_logger_level` (:135–151); module-level creations — linkedin/__init__.py:44, indeed:26, glassdoor:32, ziprecruiter:33, naukri:38, bayt:19, bdjobs:39, google/util.py:5; tuning point `jobspy/__init__.py:68` (`set_logger_level(verbose)`, AFTER site imports); display fixups + finish log `jobspy/__init__.py:107–111`.
**Signature:** `create_logger(name) -> logging.Logger` namespaced `JobSpy:{name}`; `set_logger_level(verbose: int)` mapping {0: ERROR, 1: WARNING, 2: INFO}.
**Data Shape:** each site module runs log = create_logger("<Name>") at IMPORT time; scrape_jobs' body then retunes every existing JobSpy:* logger per verbose.

### Decisive source
```python
# util.py
logger = logging.getLogger(f"JobSpy:{name}"); logger.propagate = False
if not logger.handlers:                      # idempotent across re-imports
    logger.setLevel(logging.INFO); ...add StreamHandler...

# util.py — unknown values silently fall back to INFO; ValueError branch is dead
level_name = {2: "INFO", 1: "WARNING", 0: "ERROR"}.get(verbose, "INFO")
for logger_name in logging.root.manager.loggerDict:
    if logger_name.startswith("JobSpy:"): logging.getLogger(logger_name).setLevel(level)

# __init__.py — fixups keep the finish log on the SAME module-level logger
cap_name = site.value.capitalize()
site_name = "ZipRecruiter" if cap_name == "Zip_recruiter" else cap_name
site_name = "LinkedIn" if cap_name == "Linkedin" else cap_name
create_logger(site_name).info(f"finished scraping")
```

**Flow:** import jobspy -> eight JobSpy:{Name} loggers born at INFO with one handler each -> scrape_jobs body calls set_logger_level(verbose) -> all existing JobSpy:* loggers retuned -> adapters log through their module 'log'; per-site finish line lands on the identical logger object thanks to the capitalize fixups.
**Invariant:** import-before-tune — the verbose retune only reaches loggers that EXIST when set_logger_level runs; it works here solely because site modules create loggers during package import. Unknown verbose never raises (fallback INFO makes the ValueError branch unreachable). Docstring contradiction recorded: set_logger_level claims '(default=2, all logs)' while scrape_jobs defaults verbose=0 (ERROR-only). propagate=False isolates JobSpy output from the host root logger.
**Probe:** no runtime logging probe without pandas (block recorded). Deterministic evidence: grep of all create_logger( call sites (8 module-level + 1 in scrape_site), module-level getLogger scan (only inside create_logger/set_logger_level), signature anchor verbose: int = 0 at __init__.py:50.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "JobSpy", query: "create_logger set_logger_level JobSpy verbose", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt namespaced propagate=False loggers with add-handler-once idempotence and a single post-import verbosity pass. Adapt the level map to your CLI contract. Omit the docstring/default contradiction and the stringly-typed display fixups — derive logger identity from Site.value directly. Coverage caveat: ordering behavior pinned by source anchors, not executed at runtime.

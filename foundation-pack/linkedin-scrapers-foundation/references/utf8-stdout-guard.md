<!-- capsule-v2 -->
# UTF-8 stdout guard — why does emoji-printing CLI automation crash on some consoles, and what is the minimal precondition?

**Source:** hassan-sales-nav-profiles-scraper (no LICENSE file in tree — pattern-only) `main@e294ac09c9b9`; Codebase Memory `hassan-sales-nav-profiles-scraper` (coverage `no_recorded_issue`+`metadata_match`). **Question:** what two lines make a scraper that prints ✅/❌/🌟/🎉 status markers safe on a cp1252/latin-1 console?

## detect-and-reconfigure stdout in place, before any print
**Path/Symbol:** `linkedin_scraper.py` module top level (:14–15) — executes at import time, before `main()` and every status print.
**Signature:** `if sys.stdout.encoding.lower() != 'utf-8': sys.stdout.reconfigure(encoding='utf-8')`.
**Data Shape:** mutates the EXISTING `sys.stdout` TextIOWrapper in place (keeps the same fd/redirection target); no wrapper replacement, no global locale change.

### Decisive source
```python
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
```

**Flow:** import time → compare the effective stdout encoding case-insensitively against utf-8 → reconfigure in place → all later emoji-bearing prints (`❌` :72, `✅` :76/:226, `🌟` :232, `🎉` :258) are safe regardless of console codepage.
**Invariant:** the guard must run BEFORE the first print; reconfiguring preserves the underlying stream (pipes/redirects keep working — only the codec changes). The `.lower()` comparison tolerates `UTF-8` casing variants.
**Probe:** repo has no tests; behavioral RED/GREEN executed against the mechanism itself — coverage caveat recorded. Executed probes: RED `PYTHONIOENCODING=latin-1 python3 -c "import sys; print('\U0001F31F')"` ⇒ exit 1 `UnicodeEncodeError: 'latin-1' codec can't encode character '\U0001f31f'`; GREEN same command preceded by these two verbatim lines ⇒ exit 0, marker printed; byte-exact `grep -n "sys.stdout.encoding.lower() != 'utf-8'" linkedin_scraper.py` ⇒ :14, `grep -n "sys.stdout.reconfigure(encoding='utf-8')" linkedin_scraper.py` ⇒ :15. Repo ships a Windows binary (`linkedin_scraper.exe`) where cp1252 defaults make this load-bearing.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "hassan-sales-nav-profiles-scraper", query: "main", limit: 3 });
// ⇒ rank#1 …linkedin_scraper.main :33–259 (executed: resolved rank#1); the guard itself sits at module
// top level :14–15 OUTSIDE any function node — name-only index cannot see it; RED/GREEN probe + greps stand in.
```

## Verdict
Adopt as a one-line portability precondition for ANY automation CLI whose logs/status vocabulary contains non-ASCII markers; adapt to hosts using logging frameworks by reconfiguring the handler stream equivalently; omit nothing — but do not rely on it for file output (file writes need their own explicit encodings). Contrast: string-outcome-channel defines WHAT is printed per outcome; this seam guarantees the console can render it at all.

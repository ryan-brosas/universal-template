<!-- capsule-v2 -->
# CDP-attach run-shell ownership — when Playwright attaches to a browser another program launched, what must the run shell adopt, handle, and deliberately NOT do?

**Source:** hassan-sales-nav-profiles-scraper (no LICENSE file in tree — pattern-only) `main@e294ac09c9b9`; Codebase Memory `hassan-sales-nav-profiles-scraper` (coverage `no_recorded_issue`+`metadata_match`; trace `main → start_adspower_browser` hop-1). **Question:** whose process is the browser after `connect_over_cdp`, and what does the attaching script owe the operator's live session?

## manual driver start + first-context/page adoption + intentional non-close
**Path/Symbol:** `linkedin_scraper.py:main` (:99–117) attach/adoption; (:253–259) interrupt/catch-all/finally. The WS URL comes from an external anti-detect manager (`start_adspower_browser` :17–31 — endpoint/key details owned by browser-fingerprint-stealth, omitted here).
**Signature:** `p = sync_playwright().start()` (NOT a context manager); `browser = p.chromium.connect_over_cdp(ws_url)`; adoption: `browser.contexts[0]` / `context.pages[0]`, else create.
**Data Shape:** attach yields the EXISTING context/page of the managed profile — logged-in tabs and profile state come free; creating instead of adopting would open a fresh blank context outside that session.

### Decisive source
```python
# Start Playwright manually to prevent automatic stopping
p = sync_playwright().start()
browser = p.chromium.connect_over_cdp(ws_url)

contexts = browser.contexts
if contexts:
    context = contexts[0]          # ADOPT the manager's live profile context
else:
    context = browser.new_context()
pages = context.pages
if pages:
    page = pages[0]                # reuse its existing tab (session state intact)
else:
    page = context.new_page()
# ... finally: (:257-259)
print(f"🎉 Done! Total {total_profiles} profiles saved to Google Sheets")
# Intentionally not calling p.stop() or browser.close() to keep AdsPower managed browser open
```

**Flow:** start the driver manually so no with-block can stop it mid-run → attach over CDP to the externally launched browser → adopt first existing context, else create → adopt its first page, else open one → run the harvest loop under top-level guards: `KeyboardInterrupt` prints a graceful interrupt note, any other Exception prints and is swallowed (:253–256) → `finally` ALWAYS reports the cumulative `total_profiles` count and returns WITHOUT closing browser or driver.
**Invariant:** ownership decides teardown — the process that LAUNCHED Chrome owns its lifecycle, and an attacher must leave it alive (the operator's anti-detect session survives the script by design; README Notes confirms "intentionally left open … to preserve the session"). Adoption-before-creation keeps the authenticated tab; creation is only the empty-profile fallback. Top-level handlers convert crash/interrupt into a summary report — honest caveat: the catch-all also pins exit code 0 on real faults, acceptable for a personal CLI, wrong for supervised jobs.
**Probe:** repo has no tests — coverage caveat recorded (source-grounded; attach behavior needs the external manager, not reproducible offline). Executed probes: `grep -n "connect_over_cdp" linkedin_scraper.py` ⇒ :101 exactly (single attach site); `grep -n "sync_playwright().start()" linkedin_scraper.py` ⇒ :100; `grep -n "Intentionally not calling" linkedin_scraper.py` ⇒ :259; `grep -n "except KeyboardInterrupt\|except Exception as e:\|finally:" linkedin_scraper.py` ⇒ :253/:255/:257.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "hassan-sales-nav-profiles-scraper", name_pattern: "^(main|start_adspower_browser)$" });
// ⇒ both real symbols resolve: main :33–259 (attach/adoption owner), start_adspower_browser :17–31
// (executed: 2 rows). Name-only index — body keywords return 0 by construction; greps :100/:101/:259 stand in.
```

## Verdict
Adopt the ownership rule (attacher never closes), manual `.start()` when teardown must be decoupled from block scope, adopt-first/else-create context+page ladder, and the finally-block cumulative summary; adapt handler verbosity and exit-code discipline to host supervision requirements; omit vendor attach details (see browser-fingerprint-stealth for the stealth angle of the same attach). Contrast: zombie-browser-teardown and browser-lifecycle-teardown codify OWN-AND-KILL for self-launched browsers; this capsule is the mirror contract for MANAGED browsers — pick by who launched Chrome, never mix them.

<!-- capsule-v2 -->
# Interactive prerequisite gates — how does each platform flow refuse to run before its dependency exists, and what does the LinkedIn input loop normalize that the shared one doesn't?

**Source:** Scout MIT `main@171503bf8c56d61fd6462ff08c557ec0b7fafa34`; Codebase Memory `Scout`. **Question:** Where do platform flows check their prerequisites (and why there), and what extra input normalization does cookie-gated LinkedIn need?

## Cookie gate BEFORE header render + five-step remedy + /in/-URL extraction

**Path/Symbol:** `scout.py` — `scrape_linkedin_interactive` cookie gate (:585-599) and `/in/` input loop (:603-618), lazy-import-per-flow pattern (:575/:586/:630/:641/:668/:679/:727), `scrape_from_file` LinkedIn re-gate (:797-800).

**Signature:** prerequisite = `os.environ.get('LINKEDIN_COOKIE', '').strip()`; falsy ⇒ print remedy, `return` (never raise).

### Decisive source

```python
def scrape_linkedin_interactive():
    from app.scrapers.linkedin import scrape_linkedin_profile
    cookie = os.environ.get('LINKEDIN_COOKIE', '').strip()
    if not cookie:
        console.print(Rule("[bold yellow]LinkedIn Cookie Required[/bold yellow]", ...))
        console.print("  1. Open Chrome > linkedin.com (logged in)")
        ...
        console.print("  4. Add to .env: LINKEDIN_COOKIE=your_value")
        console.print("  5. Restart Scout")          # ← env is read at FLOW START
        return
    _platform_header("LinkedIn", "Using session cookie")
    ...
    while True:
        entry = Prompt.ask("Username/URL", default="")
        entry = entry.strip().rstrip('/')
        if '/in/' in entry:
            entry = entry.split('/in/')[-1]        # full profile URL accepted
        entry = entry.lstrip('@').strip()
```

**Flow:** every `*_interactive` flow runs three phases in fixed order — optional per-platform import, prerequisite check, then `_platform_header` → collection → loop/export. Only LinkedIn has a hard prerequisite: the `li_at` session cookie. The bulk-from-file path DUPLICATES the same check (:797-800) because it dispatches to the same scrapers through a different UI — a porter adding a gated platform must add BOTH gates or bulk mode crashes deep inside the scraper instead of refusing at the door.

**Invariant:** (1) the cookie is read when the FLOW STARTS, not at boot — settings-menu change #7 writes `.env` + os.environ in one call (`_update_env`, see env-persistence.md), so a user can configure mid-session and the NEXT LinkedIn invocation picks it up without restart, yet the printed remedy still says "Restart Scout" for the .env-file-only case (boot loader uses `os.environ.setdefault`, so real-env values win over file values — the restart advice covers stale-file edits, not fresh menu writes). (2) The remedy is numbered, imperative, and names the exact DevTools path — refusal UX is part of the contract, not an error message; the flow returns to the menu with zero side effects. (3) The `/in/` ladder exists because LinkedIn users paste full profile URLs; splitting on '/in/' and taking `[-1]` yields the slug whether or not a trailing slash survived (it's rstripped first) — the shared `_collect_usernames` cannot do this because it serves seven platforms whose identifiers never contain slashes.

**Probe:** no upstream tests. Deterministic pins: `grep -n "LINKEDIN_COOKIE" scout.py` → exactly :588 (interactive-flow reader+gate), :797 (bulk-dispatch duplicate gate), :887 (settings-menu display read), :1016 (`_update_env` persistence write) for code sites, plus UI-string mentions :596/:799 — two gates, one writer; `grep -n "split('/in/')" scout.py` → :614 only. Executable normalization probe:

```
python3 - <<'EOF'
entry = ' https://www.linkedin.com/in/satya-nadella/ '.strip().rstrip('/')
slug = entry.split('/in/')[-1].lstrip('@').strip()
assert slug == 'satya-nadella', slug
EOF
```

**Retrieve:**

```ts
await mcp.codebase-memory.search_graph({ project: "Scout", query: "linkedin interactive cookie LINKEDIN_COOKIE interactive collect", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt check-prereq-before-render + actionable-remedy-then-return as the standard shape for any credentialed flow, and duplicate the gate at EVERY dispatch site that reaches the scraper; adapt the remedy text; omit nothing — moving the check into the scraper converts a friendly menu return into a mid-batch crash.

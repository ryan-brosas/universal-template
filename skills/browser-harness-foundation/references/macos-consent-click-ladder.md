<!-- capsule-v2 -->
# macOS AppleScript consent-click ladder — how do you automate a native OS permission sheet without stealing focus?

**Source:** browser-harness MIT `main@41108b8676d4bdb58b26ab3b079c0b7b0f8f3926`; Codebase Memory `browser-harness`. **Question:** How does tooling dismiss Chrome's "Allow remote debugging?" sheet programmatically, and what status vocabulary should it return?

## Status-string AppleScript with accessibility fallback
**Path/Symbol:** `src/browser_harness/macos.py:approve_remote_debugging/run_cli/_APPLESCRIPT` (:69-131).
**Signature:** `approve_remote_debugging() -> tuple[str, str | None]`; statuses `ready | setup-required | accessibility-required | not-found | error | unsupported`.
**Data Shape:** Precondition checks return EARLY without osascript; the script walks System Events windows→sheets for a sheet named "Allow remote debugging?", recursively AXPresses an AXButton described "Allow", prints `ready`/`not-found`; 5s subprocess timeout; stderr containing "not authorized"/"assistive" maps to accessibility guidance.

### Decisive source
```python
if daemon_browser_ready():
    return "ready", None

if not _google_chrome_toggle_enabled():
    return (
        "setup-required",
        'first enable "Allow remote debugging for this browser instance" at '
        "chrome://inspect/#remote-debugging, then run `browser-harness mac-approve` again",
    )
```

**Flow:** non-Darwin ⇒ unsupported → daemon healthy ⇒ ready (no subprocess) → persistent checkbox not enabled FOR THE CHROME ROOT THE SCRIPT TARGETS ⇒ setup-required → osascript → ready / not-found (RE-CHECK daemon: user may have clicked while we looked) / accessibility-required / error.
**Invariant:** The AppleScript deliberately omits `activate` — the click happens WITHOUT bringing Chrome forward (test asserts `"activate" not in input`); the toggle check compares against `_google_chrome_root()` specifically, so an Edge-only toggle can't green-light a Chrome click; not-found is ambiguous between race-lost and absent, resolved by re-probing the daemon rather than reporting failure.
**Probe:** `tests/unit/test_macos.py:21-127` — setup-required on wrong-profile toggle; osascript only after checkbox enabled; ready-without-osascript; race-to-ready on not-found+second-ready; TimeoutExpired ⇒ accessibility guidance; unsupported off-macOS; CLI exit codes 0/1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-harness", query: "approve remote debugging macos", limit: 10, fields: ["signature", "file"] });
```

## Verdict
Adopt the early-return ladder + status-tuple contract + no-activate AXPress walk for any native-permission automation. Adapt script strings per app/locale. Omit on platforms without per-connection consent sheets.

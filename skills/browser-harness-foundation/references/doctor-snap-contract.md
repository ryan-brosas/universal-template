<!-- capsule-v2 -->
# Doctor diagnostics contract — what makes a read-only healthcheck exit-code-meaningful and agent-actionable?

**Source:** browser-harness MIT `main@41108b8676d4bdb58b26ab3b079c0b7b0f8f3926`; Codebase Memory `browser-harness`. **Question:** Which checks compose the health verdict, and how are optional subsystem failures reported?

## Row printer + snap-detect + auth-error tolerance
**Path/Symbol:** `src/browser_harness/admin.py:run_doctor/_doctor_probe_chrome_binary_for_snap/_is_snap_browser/_doctor_snap_probe_path/_doctor_short_text/run_doctor_fix_snap` (:264-337, :955-1007).
**Signature:** `run_doctor() -> int` — exit 0 iff chrome running AND daemon alive; cloud auth OPTIONAL; `row(label, ok, detail)` prints `[ok  ]`/`[FAIL]`.
**Data Shape:** Snap probe order BH_CHROME_PATH→CHROME_PATH→PATH names; realpath resolution SKIPPED when raw path already contains `/snap/` (case-insensitive); page title/url truncated to DOCTOR_TEXT_LIMIT=140.

### Decisive source
```python
def _doctor_snap_probe_path(path: str) -> str:
    raw = str(path)
    try:
        resolved = os.path.realpath(raw)
    except OSError:
        resolved = raw
    return raw if _is_snap_browser(raw) else resolved
```

**Flow:** gather version/mode/chrome-running/daemon-alive/connections/auth/latest → Linux-only snap-detect block prints confinement warning + native-install doc URL → per-connection active pages (truncated, "(no real page)" for internal URLs) → core-health exit; `doctor --fix-snap` always exits 0 with .deb install + BH_CHROME_PATH export steps.
**Invariant:** A broken stored auth file must not crash doctor (AuthError ⇒ row reason text); cloud-auth absence never affects exit status ("Core health = chrome + daemon"); snap detection preserves the tell-tale RAW path — resolving symlinks first would erase exactly the evidence being detected (test-pinned both via env var and PATH discovery); truncation keeps agent-readable output bounded.
**Probe:** `tests/unit/test_admin.py:163-282` — `/snap/chromium/...` and `/SNAP/foo` classified snap, native/empty not; env-probe AND which-probe tests assert raw symlink preserved; snap block Linux-only; bad-auth row without crash; fix-snap output contains deb URL + BH_CHROME_PATH; exact row formatting; long-text truncation.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-harness", query: "doctor snap diagnose health", limit: 10, fields: ["signature", "file"] });
```

## Verdict
Adopt two-signal core health + optional-subsystem tolerance + evidence-preserving probes. Adapt checks to your stack. Omit snap specifics outside Linux-confined hosts.

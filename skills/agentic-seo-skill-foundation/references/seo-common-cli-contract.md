<!-- capsule-v2 -->
# standalone-script CLI contract — how do 88 dependency-light scripts agree on findings, output, and missing deps?

**Source:** Agentic-SEO-Skill MIT `main@69199160`; Codebase Memory `aeo-agentic-seo-skill`. **Question:** What row shape, output duality, and guard pattern make every script's findings machine-consumable AND human-readable without a shared framework?

## issue() rows + print_json_or_text + require_* guards
**Path/Symbol:** `scripts/seo_common.py:issue` (:259-260), `print_json_or_text` (:391-396), `require_requests` (:37-40), `require_bs4` (:43-46), optional-import block (:16-24). Fan-in at pin: 46 call sites for `print_json_or_text`.
**Signature:** `issue(severity: str, message: str, url: str | None = None, evidence: str | None = None) -> dict`; `print_json_or_text(result: dict, as_json: bool, text_lines: Iterable[str]) -> None`.
**Data Shape:** A finding is exactly the 4-key dict `{severity, message, url, evidence}` — no id, no timestamp; ordering in the list carries priority. Output duality: one result dict plus a pre-rendered `text_lines` iterable; `--json` prints `json.dumps(result, indent=2, sort_keys=False)` (insertion order preserved — key order in the dict IS the report layout), otherwise each text line is printed verbatim.

### Decisive source
```python
def issue(severity: str, message: str, url: str | None = None, evidence: str | None = None) -> dict:
    return {"severity": severity, "message": message, "url": url, "evidence": evidence}   # :260
...
if as_json:
    print(json.dumps(result, indent=2, sort_keys=False))                                  # :393
else:
    for line in text_lines:
        print(line)
...
try:
    import requests
except ImportError:  # pragma: no cover - exercised by users without deps
    requests = None
...
def require_requests() -> None:
    if requests is None:
        print("Error: requests library required. Install with: pip install requests", file=sys.stderr)
        sys.exit(1)                                                                        # :40
```

**Flow:** optional third-party imports are wrapped in try/except at module top and set to `None` on ImportError (module still imports cleanly for scripts that never need them) → a script calls `require_requests()`/`require_bs4()` at the point where the dep becomes load-bearing → stderr message names the exact pip command → `sys.exit(1)` (never an exception type callers must catch) → findings accumulate as `issue(...)` rows → `main()` builds both the result dict and the human lines, then hands both to `print_json_or_text(result, args.json, lines)`.
**Invariant:** The 4-key finding shape is the cross-script join contract — the report aggregator (`report-weighted-aggregation` capsule) and CI gates consume exactly these keys; adding a fifth key silently breaks consumers that unpack positionally-by-name. `sort_keys=False` is deliberate: JSON output must render in the same visual order as the dict was built. Guards exit with code 1 and a stderr install hint so a bare `pip install -r`-less environment fails loudly but readably. Note the sibling dual-path import at :26-29 (`from lib.safe_http …` falling back to `from scripts.lib.safe_http …`) — the same "run from scripts/ OR from repo root" tolerance applied to first-party code.
**Probe:** no direct upstream test for these helpers; content pins executed at pin: `def issue(` :259 ×1, `sort_keys=False` :393 ×1, `pip install requests` :39 ×1, `pip install beautifulsoup4` :45 ×1, `from lib.safe_http import` :27 ×1, `from scripts.lib.safe_http import` :29 ×1; full suite 34 passed. The contract is additionally pinned behaviorally by every test that loads a script via `importlib.util.spec_from_file_location` (tests/test_core_seo_scripts.py:10-13) — the modules must import with no side effects even when optional deps are absent.
**Retrieve:**
```json
{"tool":"mcp__codebase-memory__search_graph","args":{"project":"aeo-agentic-seo-skill","query":"issue severity message evidence print_json_or_text require_requests","limit":5}}
```
Not executed this pass — Codebase Memory MCP surface absent in the pass-3 session; seam selected and confirmed by direct full-file read of seo_common.py (396L) at pin (recorded in verification.md). Execute on revalidation.

## Verdict
Adopt all three pieces verbatim — the 4-key finding row, the dict+lines output duality with insertion-order JSON, and the None-sentinel optional-import plus exit(1)-with-pip-hint guards are the cheapest possible shared framework. Adapt severity vocabulary if your host uses different levels, and extend the guard set per optional dep; omit nothing structural. Coverage caveat: content-pinned only (no direct unit test); the 46 consumer call sites are the behavioral surface.

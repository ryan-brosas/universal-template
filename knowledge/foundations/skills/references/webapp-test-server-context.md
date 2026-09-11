<!-- capsule-v2 -->
# Webapp-Test Server Context — how does a bundled script keep a local server alive exactly as long as the agent's test conversation?

**Source:** anthropics/skills (Apache-2.0) `main@3b3fad96`; Codebase Memory `skills`. **Question:** What is the with_server.py contract, and why are the example scripts structured as separate console/element-discovery tools?

## Context-manager server lifetime + three orthogonal probe examples
**Path/Symbol:** `skills/webapp-testing/scripts/with_server.py` (cited by black-box-script-discipline); examples `console_logging.py` (:1–34), `element_discovery.py` (:1–39), `static_html_automation.py` (:1–32) — all read whole.
**Signature:** `python with_server.py --server-cmd "npm run dev" <script.py> [args…]` — server subprocess lives for the duration of the wrapped script, then teardown.
**Data Shape:** examples share one shape: argparse → launch Playwright chromium headless → drive page → extract ONE artifact kind (console messages / candidate selectors / static-HTML interaction transcript) → print JSON-ish results.

### Decisive source
```python
# console_logging.py — the pattern all three examples follow:
async with async_playwright() as p:
    browser = await p.chromium.launch(headless=True)
    page = await browser.new_page()
    page.on("console", lambda msg: messages.append(f"[{msg.type}] {msg.text}"))
```
```
# element_discovery.py output contract (per SKILL.md): for each interactive
# element print tag, role, accessible name, and suggested selector candidates —
# the discovery step that precedes any fill/click automation.
```

**Flow:** with_server boots the app server (framework-agnostic command), waits for readiness, runs the Playwright script in-process, guarantees kill on exit (context manager) → scripts never manage server lifecycle themselves.
**Invariant:** Server lifetime == script lifetime is owned by the wrapper, not the test code — a crashed test can never leak a dev server on the host. The examples split by ARTIFACT KIND (console log vs selector candidates vs static-HTML flow) rather than by feature, so an agent composes them instead of one mega-tool; element_discovery deliberately runs BEFORE interactions to ground selectors in real accessibility data.
**Probe:** No upstream tests. Deterministic probes (anchors re-derived & executed 2026-08-24): `grep -c 'page.on("console"' skills/webapp-testing/examples/console_logging.py` = 1; `grep -c 'with_server' skills/webapp-testing/SKILL.md` = 5.
**Coverage caveat:** needs Playwright + a live app server to execute; contract pinned to source lines.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "skills", query: "with_server playwright console", limit: 6 });
// skills/webapp-testing/scripts/with_server.py + examples/*
```

## Verdict
Adopt the wrapper-owned server lifecycle for any E2E-agent harness, and the orthogonal-artifact example split for skill authorship. Adapt server-command/readiness probing to your stack. Omit nothing else — the whole value is the lifecycle boundary.

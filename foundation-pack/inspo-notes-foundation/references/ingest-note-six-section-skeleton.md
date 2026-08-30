<!-- capsule-v2 -->
# INGEST-note six-section skeleton — what fixed anatomy makes one function's capture complete and re-findable?

**Source:** user-authored ingest notes over third-party repos (internal working notes; no upstream VCS), `/mnt/hdd/utopia/inspo/reference/notes`; Codebase Memory `inspo-notes`. **Question:** What sections must every single-function ingest note carry, in what order, so a later session can reconstruct the function without re-cloning the repo?

## Fixed six-section anatomy
**Path/Symbol:** all six INGEST notes (`browser-harness-get_ws_url.md`, `browser-use-BrowserSession.connect.md`, `cuga-agent-PolicySystem.md`, `growchief-cdpDetectionPass.md`, `jobspy-scrape.md`, `pydantic-ai-harness-BrowserUse.md`); identical heading ladder at lines 1/3/6/9/17/24/29.
**Signature:** H1 = `# INGEST — <repo> · target: <symbol or subsystem>`; then fixed H2s `## 1. The function's job`, `## 2. The flow it lives in`, `## 3. Neighborhood`, `## 4. Constraints that shaped it`, `## 5. Behavior contract`, `## 6. Evidence`.
**Data Shape:** job = one-paragraph purpose; flow = end-to-end path with entry/exit; neighborhood = bullet list of adjacent symbols with one-line roles (the re-entry map); constraints = the WHY list that shaped the design; contract = Inputs / Outputs / Edges / "Correct =" acceptance line; evidence = pinned `file:line` ranges + test paths + graph stats.

### Decisive source
```markdown
# INGEST — browser-use/browser-harness · target: `get_ws_url`
...
## 5. Behavior contract
Inputs: `BU_CDP_WS` | `BU_CDP_URL` | nothing (scan). Outputs: `ws://`/`wss://` URL.
Edges: 403 permission-blocked; 404 + DevToolsActivePort path; chrome-not-running;
30s timeout on dedicated URL.
Correct = a websocket Chrome will accept for Target/Page/Runtime, not a launched
Playwright Chromium.
```
(`notes/browser-harness-get_ws_url.md:1-36`)

**Flow:** name the exact target → state its job → place it in the caller flow → enumerate the neighborhood (what to read next) → record the constraints that explain every non-obvious choice → write the testable contract incl. edge behavior → pin line-range evidence for every claim.
**Invariant:** every note carries ALL six sections with an Evidence section whose pins are real `path:lines`; the Behavior contract always ends in a "Correct = ..." acceptance sentence that distinguishes the real outcome from the plausible wrong one (a ws Chrome accepts vs a launched Playwright Chromium; joinable company strings vs firmographics; finished vs incomplete run). Probe anchors verified live: each of the six notes contains exactly six `^## [0-9].` headings (`grep -c '^## [0-9]\.'` = 6 per file) and `grep -c 'Correct ='` ≥ 1.
**Probe:** no upstream tests exist (user-authored notes) → deterministic probe: `grep -c '^## [0-9]\.' notes/<note>.md` must equal 6 and `grep -c 'Correct =' notes/browser-harness-get_ws_url.md` must be ≥ 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_code({ project: "inspo-notes", pattern: "Behavior contract", limit: 10 });
// resolves inspo-notes.<note>.5.-Behavior-contract Section nodes (the six-section skeleton contract section)
// (EXECUTED 2026-08-24 docs-knowledge pass 9: 3 result; search_graph query/name_pattern forms return 0
//  on this doc-shaped graph — Section nodes are tokenless/filtered; search_code is the working primitive)
```

## Verdict
Adopt the six-section skeleton verbatim as the template for any new single-function capture note; adapt section wording for subsystem-scale targets (e.g. cuga Policy System widens "function" to "subsystem"); omit any upstream code itself from this repo — notes point at their indexed projects instead.

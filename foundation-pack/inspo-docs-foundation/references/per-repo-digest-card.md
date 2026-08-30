<!-- capsule-v2 -->
# Per-repo digest card — what five fields make an ingested repo's summary decidable without opening the clone?

**Source:** user-authored digest docs over third-party repos (internal working notes; no upstream VCS), `/mnt/hdd/utopia/inspo/reference/docs`; Codebase Memory `docs`. **Question:** What must every per-repo ingest card contain so a reader can decide relevance, entry points, and borrow-value from the card alone?

## Fixed five-field anatomy
**Path/Symbol:** all ten repo digests (`Auto_job_applier_linkedIn.md`, `browser-use.md`, `EasyApplyJobsBot.md`, `growchief.md`, `JobSpy.md`, `LinkedIn-Easy-Apply-Bot.md`, `linkedin-private-api.md`, `linkedin-profile-scraper-api.md`, `linvo-scraper.md`, `locoagent.md`, plus `undetectable-fingerprint-browser.md`); identical ladder: H1 line 1, bold identity line 3, `Stack:` line 4, `Entry:` line 5, `Value:` line 6, `Source:` footer.
**Signature:** H1 = `# INGESTED — <repo> (<stars>★ <lang>)`; identity = `**<owner>/<repo>** — <one-line what-it-is>, <license> — <role in the batch>`; then labeled lines `Stack:`, `Entry:`, `Value:`; footer = `Source: <path> (<clone depth>, <HEAD>)` + index pointer.
**Data Shape:** Stack = language + key frameworks in one line; Entry = concrete files/dirs to open first (real paths like `app.py`, `runAiBot.py`, `config_schema.py`); Value = the decision-bearing claim naming WHAT is worth borrowing and for which product layer.

### Decisive source
```markdown
# INGESTED — browser-use (Python)

**browser-use/browser-use** — "Make websites accessible for AI agents", MIT —
the AI browser-agent framework (next-gen frontier, AI-AGENT).
Stack: Python 3.11+, Playwright-driven Chromium over CDP, Pydantic (typed tools/IO), CLI + Python library.
Entry: `browser_use/` (package; `BrowserSession` class at `browser_use/browser/session.py`), `examples/`, `browser_use/skills/` (Claude skill), `pyproject.toml`.
Value: AI browser-agent / observation frontier — attach to an existing browser via CDP (`cdp_url`), a domain allowlist (`allowed_domains`), structured output (`output_model_schema`), Pydantic custom tools; ...
```
(`docs/browser-use.md:1-6`)

**Flow:** stamp identity + role tag on the H1/identity line → compress the stack → list real entry files (never "see repo") → write Value as a specific borrow-claim with named mechanisms → close with the exact local source path and clone freshness.
**Invariant:** every card carries ALL five fields with a `Value:` line whose claim names concrete capabilities (`grep -c '^Value:' docs/<card>.md` = 1 per card across all 11 cards, verified live); Entry always cites real paths from the actual clone. The generic-praise failure mode ("great project") is excluded by construction.
**Probe:** deterministic probe: `grep -c '^Value:' docs/browser-use.md` = 1 AND `grep -c 'Source:' docs/browser-use.md` ≥ 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_code({ project: "docs", pattern: "Value:", limit: 12 });
// resolves docs.<Repo>.<repo>.md Module nodes carrying the Value: digest field (browser-use et al.)
// (EXECUTED 2026-08-24 docs-knowledge pass 9: 3 result; search_graph query/name_pattern forms return 0
//  on this doc-shaped graph — Section nodes are tokenless/filtered; search_code is the working primitive)
```

## Verdict
Adopt the five-field card as the mandatory shape for every new ingested repo; adapt field labels to your domain but keep Value decision-bearing and Entry path-real; omit star counts as quality signals — they are identity metadata, not verdicts.

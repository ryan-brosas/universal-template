<!-- capsule-v2 -->
# Card tag application boundary — where do legend role tags legally appear, and what does the card body stay clean of?

**Source:** user-authored digest docs over third-party repos (internal working notes; no upstream VCS), `/mnt/hdd/utopia/inspo/reference/docs`; Codebase Memory `docs`. **Question:** Do the closed taxonomy tags stamp every card's identity line, or only the README batch bullets — and why does the difference matter for a porter?

## Tags live in the index; cards stay tag-free (one exception)
**Path/Symbol:** `docs/browser-use.md:3` is the ONLY card whose identity line ends with a tag token: `...the AI browser-agent framework (next-gen frontier, AI-AGENT).`; the other ten cards (`Auto_job_applier_linkedIn.md`, `EasyApplyJobsBot.md`, `growchief.md`, `JobSpy.md`, `LinkedIn-Easy-Apply-Bot.md`, `linkedin-private-api.md`, `linkedin-profile-scraper-api.md`, `linvo-scraper.md`, `locoagent.md`, `undetectable-fingerprint-browser.md`) carry NO tag token anywhere in their bodies; all ten batch bullets at `docs/README.md:16-34` end with a tag.
**Signature:** batch bullet = `- **<repo>** — <stars>★ <lang> — <TAG>` (tag ALWAYS present, one per bullet); card identity line = `**<owner>/<repo>** — <what-it-is>, <license> — <role phrase>` where the role is PROSE, not a legend token — with browser-use as the single deliberate exception.
**Data Shape:** input = a repo's relation to the reference product; output = machine-comparable tag on the index bullet + human-readable role prose inside the card; the exception carries its tag inline because the card was written as a frontier-verdict ("next-gen frontier") rather than a plain member description.

### Decisive source
```markdown
## The batch
...
- **locoagent** — 1.0k★ TS — AI-AGENT
  **LocoreMind/locoagent** — AI social-media agent that operates a **real browser** autonomously.
```
(`docs/README.md:33-34`: tag on the bullet, role-as-prose on the card identity line)

vs. the exception:
```markdown
**browser-use/browser-use** — "Make websites accessible for AI agents", MIT —
the AI browser-agent framework (next-gen frontier, AI-AGENT).
```
(`docs/browser-use.md:2-3`)

**Flow:** assign the tag ONCE on the README batch bullet → write the card identity line as natural-language role description → do NOT repeat the tag token inside the card unless the card doubles as a verdict document → comparability queries run against the README, never against card bodies.
**Invariant:** tag tokens are INDEX-surface metadata, not card-body metadata: exactly 2 of 12 files in the dir contain any legend token (`grep -lE 'AI-AGENT|EASY-APPLY|SCRAPER-|FULL-PRODUCT|PRIVATE-API|STEALTH|LINVO' docs/*.md` = `browser-use.md` + `README.md`, verified live) and `grep -c '^- \*\*' docs/README.md` = 10 tagged bullets. A porter who "fixes" cards by adding tags everywhere breaks the boundary this corpus maintains.
**Probe:** deterministic probe: `grep -c 'AI-AGENT' docs/browser-use.md` = 1 AND `grep -lE 'AI-AGENT|EASY-APPLY|SCRAPER-|FULL-PRODUCT|PRIVATE-API|STEALTH|LINVO' docs/*.md | wc -l` = 2 AND `grep -c '^- \*\*' docs/README.md` = 10.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_code({ project: "docs", pattern: "next-gen frontier", limit: 5 });
// resolves docs.browser-use Module browser-use.md:1-10 — the lone card carrying an in-body tag token
// (EXECUTED 2026-08-24 thin-elevator pass: results: 1; search_graph forms return 0 on this doc-shaped
// graph — Section nodes are tokenless/filtered; search_code is the working primitive)
```

## Verdict
Adopt the boundary: tags live on index bullets, cards describe roles in prose; adapt which surface carries tags if your tooling differs but keep ONE canonical machine-readable surface; omit per-card tag stamps when porting — the lone browser-use exception documents a verdict-card style, not the rule (this capsule corrects the taxonomy capsule's Flow claim that the same token is reused inside card identity lines).

<!-- capsule-v2 -->
# Card supremacy analog line — how does a digest card flag "this repo is the architecture-level twin" without breaking the five-field ladder?

**Source:** user-authored digest docs over third-party repos (internal working notes; no upstream VCS), `/mnt/hdd/utopia/inspo/reference/docs`; Codebase Memory `docs`. **Question:** When one batch member is the closest analog of the reference product, where does the card record that supremacy claim so it neither dilutes the five labeled fields nor gets lost in prose?

## Supremacy bold line between identity and Stack
**Path/Symbol:** `docs/growchief.md:4` (`**Best full-stack architectural analog to LinkedHelper's product surface.**`) and `docs/linvo-scraper.md:4` (`**Closest architectural analog to LinkedHelper** — a commercial SaaS that open-sourced its engine.`); the other nine cards have no such line.
**Signature:** optional line 4 = `**<superlative> <relation> to <reference product>**` — a standalone full-bold sentence, never prefixed with a field label, always positioned after the identity line (line 3) and before `Stack:` (line 5).
**Data Shape:** input = the porter's judgment that a repo is not merely a layer-analog but THE whole-product twin; output = zero or one supremacy line per card (never multiple); the claim names the reference product explicitly ("LinkedHelper") and states WHY (what was open-sourced).

### Decisive source
```markdown
# INGESTED — linvo-scraper (628★ TS)

**linvo-scraper** — "LinkedIn Automation Bot with every possible scraping", MIT, used by the Linvo.io SaaS.
**Closest architectural analog to LinkedHelper** — a commercial SaaS that open-sourced its engine.
Stack: TypeScript, ts-node, Selenium-driven browser automation.
```
(`docs/linvo-scraper.md:1-4`; the twin instance is `docs/growchief.md:4`)

**Flow:** identity line states what the repo IS → if (and only if) the repo is the whole-product architectural twin, insert ONE unlabeled bold supremacy line naming the reference product and the reason → resume the standard ladder at `Stack:` → readers scanning for "which repo do I study first" read line 4 without parsing any labeled field.
**Invariant:** the supremacy line is UNLABELED by design — it must never masquerade as one of the five fields (`Stack:`/`Entry:`/`Value:` stay exactly once per card); it is optional: exactly 2 of 11 cards carry it (`grep -lE '^\*\*(Best|Closest)' docs/*.md | wc -l` = 2, verified live), so its absence carries no meaning while its presence is a routing verdict.
**Probe:** deterministic probe: `grep -c '^\*\*Best full-stack' docs/growchief.md` = 1 AND `grep -c '^\*\*Closest architectural' docs/linvo-scraper.md` = 1 AND `grep -lE '^\*\*(Best|Closest)' docs/*.md | wc -l` = 2.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_code({ project: "docs", pattern: "Best full-stack", limit: 5 });
// resolves docs.growchief Module growchief.md:1-11 (EXECUTED 2026-08-24 thin-elevator pass: results: 1;
// search_graph query/name_pattern forms return 0 on this doc-shaped graph — Section nodes are tokenless/
// filtered; search_code is the working primitive)
```

## Verdict
Adopt the optional unlabeled bold supremacy line at position 4 for whichever single repo is the reference product's whole-product twin; adapt the superlative wording to your domain but keep the explicit product name and open-sourcing reason; omit the line for mere layer-analogs — spreading supremacy across many cards destroys its routing value.

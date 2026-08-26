<!-- capsule-v2 -->
# Closed capability taxonomy — how do legend-defined role tags keep a growing repo batch comparable?

**Source:** user-authored digest docs over third-party repos (internal working notes; no upstream VCS), `/mnt/hdd/utopia/inspo/reference/docs`; Codebase Memory `docs`. **Question:** How is a batch of ingested repos categorized so every member's role is comparable without free-text category drift?

## Legend-first closed tags
**Path/Symbol:** `README.md:6-13` (`## Legend (relation to LinkedHelper anatomy)` block); tags applied in the batch bullets at lines 16-34 and inside individual cards (e.g. `browser-use.md:3` ends `AI-AGENT)`).
**Signature:** legend entry = `- <TAG> — <definition sentence>`; application = trailing token on identity lines and batch bullets, e.g. `- **JobSpy** — 4.1k★ Python — SCRAPER-LIB`.
**Data Shape:** seven closed tags with `SCRAPER-*` as a prefix family: FULL-PRODUCT / PRIVATE-API / SCRAPER-* (LIB, PUPPETEER) / EASY-APPLY (incl. -2 for the second instance) / STEALTH / AI-AGENT / LINVO. Each tag names a relation to the reference product's anatomy, not a technology.

### Decisive source
```markdown
## Legend (relation to LinkedHelper anatomy)
- FULL-PRODUCT — full SaaS product open-sourced (architecture-level analog)
- PRIVATE-API — API-layer automation (vs DOM)
- SCRAPER-* — data extraction layers
- EASY-APPLY — job-application bots (LH's core workflow)
- STEALTH — fingerprint/multi-account layer
- AI-AGENT — LLM-driven browser automation (next-gen)
- LINVO — direct LH equivalent engine
```
(`docs/README.md:6-13`)

**Flow:** define the tag vocabulary once in the README legend → stamp exactly one tag per batch bullet → reuse the same token inside the card's identity line → when a tenth kind of relation appears, add it to the legend first, then use it.
**Invariant:** the vocabulary is closed and legend-owned: all ten batch bullets carry a tag drawn from this exact set (`grep -c '^- \*\*' docs/README.md` = 10, verified live); numeric suffixes (-2) distinguish same-role instances instead of inventing new roles.
**Probe:** deterministic probe: `grep -c '^## Legend' docs/README.md` = 1 AND `grep -c '^- \*\*' docs/README.md` = 10.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_code({ project: "docs", pattern: "Legend", limit: 5 });
// resolves docs.README.Legend-(relation-to-LinkedHelper-anatomy) @ README.md:6
// (EXECUTED 2026-08-24 docs-knowledge pass 9: 1 result; search_graph query/name_pattern forms return 0
//  on this doc-shaped graph — Section nodes are tokenless/filtered; search_code is the working primitive)
```

## Verdict
Adopt legend-first closed tagging for any inspiration-batch index; adapt the specific tags to your product anatomy; omit hierarchical or faceted classification — one comparable role token per repo proved sufficient and stays grep-checkable.

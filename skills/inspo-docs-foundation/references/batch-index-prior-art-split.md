<!-- capsule-v2 -->
# Batch vs prior-art index split — how does an ingest README keep fresh clones and already-indexed repos from being re-ingested?

**Source:** user-authored digest docs over third-party repos (internal working notes; no upstream VCS), `/mnt/hdd/utopia/inspo/reference/docs`; Codebase Memory `docs`. **Question:** How must the index document separate "this batch" from "already ingested" so no repo gets cloned or digested twice?

## Two disjoint index sections
**Path/Symbol:** `README.md:15-34` (`## The batch`, ten bold-tagged bullets) vs `README.md:48-51` (`## Already-ingested prior art in this dir (not part of this batch)`, three entries).
**Signature:** batch bullet = `- **<repo>** — <stars>★ <lang> — <TAG>` + one indented identity line; prior-art entry = `- <dir-name>/ — <what it is> (<pointer to its own basis doc>)`.
**Data Shape:** batch members are NEW clones with digest cards named `<repo>.md` in this same directory; prior art is repos indexed elsewhere with their own docs — explicitly excluded from this batch's card set.

### Decisive source
```markdown
## Already-ingested prior art in this dir (not part of this batch)
- `linked-helper-extract/` — the LH v2.130.5 raw extract (see lh-basis)
- `browser-use/` — AI browser agent framework (Python)
- `linkedin_scraper/` — joeyism Python library
```
(`docs/README.md:48-51`)

while the batch section above carries only new members:
```markdown
## The batch
- **linvo-scraper** — 628★ TS — LINVO
  **linvo-scraper** — "LinkedIn Automation Bot with every possible scraping", ...
```
(lines 15-16)

**Flow:** open the README → `## The batch` lists what THIS ingestion round added, each with a card in this directory → `## Already-ingested prior art` lists everything already served by other indexes → any discovery hit found in prior art stops there instead of minting a duplicate card.
**Invariant:** the two sections are disjoint: browser-use appears in prior art AND has a card only because its card documents the existing clone for this batch's context — but it is NOT re-listed as a batch bullet (`grep -c '^## Already-ingested' docs/README.md` = 1, verified live); each prior-art entry points to where its real documentation lives.
**Probe:** deterministic probe: `grep -c '^- \*\*' docs/README.md` = 10 (batch only) AND `grep -c 'Already-ingested' docs/README.md` = 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_code({ project: "docs", pattern: "Already-ingested", limit: 5 });
// resolves docs.README.Already-ingested-prior-art-in-this-dir-(not-part-of-this-batch) @ README.md:48
// (EXECUTED 2026-08-24 docs-knowledge pass 9: 1 result; search_graph query/name_pattern forms return 0
//  on this doc-shaped graph — Section nodes are tokenless/filtered; search_code is the working primitive)
```

## Verdict
Adopt the two-section index shape for any cumulative inspiration library; adapt section titles freely but keep them mutually exclusive and pointer-bearing; omit cross-batch dedupe tooling — the disjoint-sections discipline is the mechanism.

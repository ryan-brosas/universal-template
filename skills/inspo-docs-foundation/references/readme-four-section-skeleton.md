<!-- capsule-v2 -->
# README four-section skeleton — what fixed section order makes an ingest index navigable before any card is opened?

**Source:** user-authored digest docs over third-party repos (internal working notes; no upstream VCS), `/mnt/hdd/utopia/inspo/reference/docs`; Codebase Memory `docs`. **Question:** What is the complete top-level section contract of the index document, and in what order must its parts appear?

## Four H2 sections: legend → batch → mapping → prior art
**Path/Symbol:** `docs/README.md` — exactly 4 `^## ` headings (verified live): line 6 `## Legend (relation to LinkedHelper anatomy)`, line 15 `## The batch`, line 37 `## How they map to the LinkedHelper stack`, line 48 `## Already-ingested prior art in this dir (not part of this batch)`; the file opens with a two-paragraph preamble (`# INSPO INDEX — ...` title + "Collection cloned as basis material..." context naming the sibling basis ingestion).
**Signature:** `<# INSPO INDEX — <domain> basis>` → context paragraph(s) → `## Legend (<tag vocabulary definition>)` → `## The batch` (one tagged bullet per member, each with a card in this dir) → `## How they map to the <reference product> stack` (layer→analog table) → `## Already-ingested prior art ...` (pointer list).
**Data Shape:** the four sections are the closed set — no additional H2 exists; each has exactly one instance; their order encodes the reading ladder: vocabulary first, then inventory, then synthesis, then exclusion.

### Decisive source
```markdown
## Legend (relation to LinkedHelper anatomy)
...
## The batch
...
## How they map to the LinkedHelper stack
...
## Already-ingested prior art in this dir (not part of this batch)
```
(`docs/README.md` headings at lines 6, 15, 37, 48; `grep -c '^## ' docs/README.md` = 4)

**Flow:** reader opens the index → Legend defines the tag vocabulary used everywhere below → The batch lists this round's members with cards alongside → the mapping table synthesizes members into reference-product layers → prior art excludes everything already served elsewhere. New sections are NOT appended for one-off notes; they go into cards or the library-level catalog.
**Invariant:** the section set is CLOSED at four and ordered as defined — `grep -c '^## ' docs/README.md` = 4 with zero extra H2s (verified live); every batch bullet's repo has a same-directory card; the mapping table references only batch members; prior art never duplicates a batch bullet.
**Probe:** deterministic probe: `grep -c '^## ' docs/README.md` = 4 AND `grep -n '^## ' docs/README.md` lists Legend/The batch/How they map/Already-ingested in that order.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_code({ project: "docs", pattern: "^## ", limit: 10 });
// resolves the docs.README Module carrying all four Section nodes (EXECUTED 2026-08-24 thin-elevator pass:
// pattern-form search_code is the working primitive on this doc-shaped graph — search_graph query/
// name_pattern forms return 0 because Section nodes are tokenless)
```

## Verdict
Adopt the four-section order (vocabulary → inventory → synthesis → exclusion) as the fixed index skeleton for any digest corpus; adapt section titles and the domain of the mapping table; omit ad-hoc extra sections — if a fifth concern appears, it belongs in a card field or the library catalog, not a new H2 here.

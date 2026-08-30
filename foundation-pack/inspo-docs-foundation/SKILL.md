---
name: inspo-docs-foundation
description: "Use when building an ingest-digest layer over a cloned inspiration batch — one digest card per repo, a closed capability taxonomy, a source-product→analog mapping table, and an index that separates the current batch from already-ingested prior art."
disable-model-invocation: true
---
# inspo-docs: per-repo ingest-digest index foundation

## Use this for
Use when building an ingest-digest layer over a cloned inspiration batch — one digest card per repo, a closed capability taxonomy, a source-product→analog mapping table, and an index that separates the current batch from already-ingested prior art. Source digests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `references/per-repo-digest-card.md` — the fixed five-field card every ingested repo gets, and why Value is its own labeled line.
- `references/capability-taxonomy-tags.md` — the closed seven-tag vocabulary stamped on every batch member.
- `references/layer-analog-mapping-table.md` — the two-column table that binds each proprietary layer to its OSS analog.
- `references/batch-index-prior-art-split.md` — how the README separates "this batch" from prior art so re-ingest never duplicates.
- `references/readme-four-section-skeleton.md` — the closed four-section index order (legend → batch → mapping → prior art) every ingest README follows.
- `references/card-supremacy-analog-line.md` — the optional unlabeled bold line that flags THE whole-product twin without breaking the five-field ladder.
- `references/card-tag-application-boundary.md` — why tags live on README bullets while card bodies stay tag-free (browser-use being the lone verdict-card exception).
- `references/source-footer-freshness-dialects.md` — the one-line `Source:` footer pairing clone depth with a depth-matched freshness stamp (+ live pointer-drift note).

## Capsule map
- **Digest card** — `per-repo-digest-card`: H1 + bold identity line → Stack → Entry points → Value → Source footer; Value carries the decision-bearing claim, never generic praise.
- **Capability tags** — `capability-taxonomy-tags`: seven closed tags (FULL-PRODUCT / PRIVATE-API / SCRAPER-* / EASY-APPLY / STEALTH / AI-AGENT / LINVO) defined once in the legend, applied in every card and batch bullet.
- **Layer mapping** — `layer-analog-mapping-table`: LH compiled layer ↔ OSS analog table; multi-cover rows name several repos, coverage gaps stay visible as uncovered layers.
- **Batch/prior-art split** — `batch-index-prior-art-split`: `## The batch` bullets vs `## Already-ingested prior art` list keep fresh clones and previously indexed repos disjoint.
- **Index skeleton** — `readme-four-section-skeleton`: closed four-H2 order legend → batch → mapping table → prior art; no ad-hoc sections, reading ladder encoded in the order.
- **Supremacy line** — `card-supremacy-analog-line`: optional unlabeled bold line 4 (`**Closest architectural analog to LinkedHelper**…`) flags THE whole-product twin on growchief + linvo only; never a labeled field, absence carries no meaning.
- **Tag boundary** — `card-tag-application-boundary`: tags stamp README bullets (10/10) while card bodies stay tag-free; browser-use is the lone verdict-card exception carrying `(next-gen frontier, AI-AGENT)` inline.
- **Footer freshness** — `source-footer-freshness-dialects`: one-line footer pairs clone depth with depth-matched stamps (shallow → "fresh HEAD" ×10; full → SHA+version+date ×1) plus a uniform See-pointer now drifted to INSPO.md.

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
User-authored digest docs over third-party repos (internal working notes; no upstream VCS), plain directory `/mnt/hdd/utopia/inspo/reference/docs` (no git metadata); Codebase Memory project `docs` (42 nodes / 41 edges, ready, verified live 2026-08-23; doc-shaped Section/File graph — contracts confirmed by whole-file reads, not call-graph traces).
Thin-elevator pass 4 (cron drain-thin-elevator 2026-08-24, refs 4→8): four new capsule-v2 mined whole-corpus — index skeleton, supremacy line, tag boundary, footer freshness dialects; all probes + retrieves live-executed; tag-boundary capsule corrects taxonomy capsule's overclaiming Flow step.

## Full view (memory graph)
Revalidate `docs` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims.
Doc-shaped-graph caveat (recurring): `search_graph` query/name_pattern forms return total:0 on this corpus — only Function-class nodes carry searchable tokens and this corpus has none. The working retrieval primitive is `search_code --pattern '<needle>'` (or CLI JSON form), which resolves Module/Section nodes line-exact.

## Boundaries
Adopt the digest formats (five-field cards, closed tag taxonomy, analog mapping table, batch/prior-art split, four-section index skeleton); adapt the specific tags and layer names to your product domain; omit the described third-party products' internals (each lives in its own indexed inspo project/foundation).

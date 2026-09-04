<!-- capsule-v2 -->
# Change-coupling edges — how do you mine "these files change together" from git history without noise?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What commit filters and thresholds turn `git log --name-only` into trustworthy FILE_CHANGES_WITH edges?

## Trackable filter + 20-file cap + 3-co-change floor + last_co_change
**Path/Symbol:** `src/pipeline/pass_githistory.c:cbm_compute_change_coupling` (258–341), `cbm_is_trackable_file` (49–88), constants (line 15: `GH_MIN_COMMITS = 3, GH_MAX_FILES = 20`).
**Signature:** `int cbm_compute_change_coupling(const cbm_commit_files_t *commits, int commit_count, cbm_change_coupling_t *out, int max_out);`
**Data Shape:** Per pair: canonical order (`\x01`-joined key), co_change_count ≥3, coupling_score ≥0.7, and `last_co_change` = MAX timestamp across the pair's commits. History window: `git log --name-only --since="1 year ago" --max-count=10000`.

### Decisive source
```c
if (commits[c].count > GH_MAX_FILES) continue;   /* bulk-refactor/mass-rename commits */
...
/* Parallel table mapping pair_key → max commit timestamp ... so the resulting
 * edge can carry last_co_change. */
```
```c
/* Skip lock files / vendor dirs / minified+binary suffixes before counting */
```

**Flow:** parse bounded git log (validated path arg) → drop non-trackable files and oversized commits → count unordered file pairs via hash tables (pair_counts + pair_timestamps in parallel) → emit pairs meeting floor/threshold with recency stamp → pass applies them as FILE_CHANGES_WITH edges; compute runs on a side thread when workers >1.
**Invariant:** Filters run BEFORE counting — one mass-rename commit otherwise poisons every pair; recency must be the max, not the first-seen timestamp.
**Probe:** `tests/test_pipeline.c:githistory_compute_coupling` (a+b=3 co-changes, score ≥0.7), `githistory_coupling_carries_last_co_change` (max of three timestamps wins), `githistory_skip_large_commits`, `githistory_is_trackable`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_compute_change_coupling", limit: 5 });
```

## Verdict
Adopt the filter-then-count pipeline and dual frequency/recency scoring; adapt trackable-file rules to your repo; omit the temporal per-file series if you only need coupling edges.

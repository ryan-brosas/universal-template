<!-- capsule-v2 -->
# udiff apply pipeline — dedupe, normalize, then a context-shrinking partial-hunk ladder

**Source:** Aider Apache-2.0 `main@5dc9490bb35f9729ef2c95d00a19ccd30c26339c`; Codebase Memory project `aider` (full index). **Question:** How do you apply model-authored unified-diff hunks when their context lines have drifted from the real file, without ever applying the wrong hunk to the wrong place?

## Parse → dedupe/normalize → direct → sectioned → context-shrink
**Path/Symbol:** `aider/coders/udiff_coder.py`: `UnifiedDiffCoder.apply_edits(edits)` (:69), `apply_hunk(content, hunk)` (:151), `directly_apply_hunk(content, hunk)` (:261), `make_new_lines_explicit(content, hunk)` (:209), `apply_partial_hunk(...)` (:282), `normalize_hunk(hunk)` (:250), `hunk_to_before_after(hunk, lines=False)` (:403).
**Signature:** hunks are lists of prefixed lines (`" ctx"`, `"-old"`, `"+new"`); `apply_edits -> None | raise ValueError` aggregating per-hunk errors.
**Data Shape:** dedupe key = `path + "\n" + normalized-hunk` (exact duplicate hunks collapse); `normalize_hunk` re-derives the diff from before/after via `difflib.unified_diff(before, after, n=max(len(before), len(after)))`, dropping the 3 header lines.

### Decisive source
```python
# apply_partial_hunk: shrink context until SOMETHING unique anchors the change
for drop in range(use_all + 1):          # total context lines to give up
    use = use_all - drop
    for use_prec in range(len_prec, -1, -1):   # prefer dropping FOLLOWING first
        if use_prec > use:
            continue
        use_foll = use - use_foll_guard(use, use_prec)
        this_prec = preceding_context[-use_prec:]
        this_foll = following_context[:use_foll]
        res = directly_apply_hunk(content, this_prec + changes + this_foll)
        if res:
            return res
```
And the tiny-anchor guard that keeps shrinking safe:
```python
before_lines = "".join([line.strip() for line in before_lines])
# Refuse to do a repeated search and replace on a tiny bit of non-whitespace context
if len(before_lines) < 10 and content.count(before) > 1:
    return    # ambiguous micro-anchor ⇒ this rung fails instead of editing the wrong copy
```

**Flow:** `apply_hunk` first tries the whole hunk directly; on failure re-expands the hunk's "before" against the real file (`make_new_lines_explicit`: diff before↔content, keep non-`+` lines, rebuild the hunk — abandoned if the rebuilt before shrinks below 66% or 10 chars); splits ops into sections (context/change alternation) and applies each change-section with its surrounding contexts via the partial ladder; any failed section aborts the whole hunk (all_done=False).
**Invariant:** every leaf application is exact-substring replace through `flexi_just_search_and_replace` (search_and_replace × all_preprocs ONLY — no cherry-pick/DMP rungs here); ambiguity fails LOUD with typed errors carrying the offending lines and counts (`no_match_error` / `not_unique_error`) plus `other_hunks_applied` note when some hunks succeeded; empty-before hunks append after_text (file-create/append path).
**Probe:** `tests/basic/test_udiff.py::test_find_diffs_single_hunk` (:8), `::test_find_diffs_dev_null` (:29), `::test_find_diffs_dirname_with_spaces` (:50), `::test_find_multi_diffs` (:71) pin the PARSER; executed this run: `.pi/work/foundations-deep-farm/scratch-aider-pass2/probe_gate5.py::udiff-partial-hunk-ladder` (stale leading context rescued by shrink ladder) + `::udiff-apply-sections` (two change-sections land independently), repo venv GREEN. No upstream tests cover the apply side.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "aider", name_pattern: "apply_partial_hunk", limit: 5 });
// also resolves: apply_hunk, make_new_lines_explicit, hunk_to_before_after, find_diffs
```

## Verdict
Adopt the whole pipeline: normalization+dedupe before apply, sectioned application, context-shrinking with the <10-char repeated-anchor refusal, and typed aggregate errors; adapt the error copy and the 0.66/10-char thresholds; omit `find_diffs`' fence grammar if your host parses diffs upstream of the coder. Coverage caveat: parser has direct tests; APPLY-side behavior pinned only by this run's executed probes.

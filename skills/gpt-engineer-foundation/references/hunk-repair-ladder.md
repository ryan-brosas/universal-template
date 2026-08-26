<!-- capsule-v2 -->
# hunk-repair-ladder — How are wrong line numbers, skipped lines, and stray comments repaired inside a hunk?

**Source:** gpt-engineer MIT `main@a90fcd54`; Codebase Memory `gpt-engineer`. **Question:** What is Hunk.validate_and_correct's decision ladder for anchoring and correcting a hunk against real file lines?

## Hunk validation/correction seam
**Path/Symbol:** `gpt_engineer/core/diff.py:Hunk.find_start_line` (:133-198), `Hunk.validate_lines` (:200-286), helpers `is_similar`/`count_ratio` (:381-419).
**Signature:** `validate_and_correct(lines_dict: dict, problems: list) -> bool` where lines_dict = OrderedDict{1-based line_no: line_content}.
**Data Shape:** Mutates self.lines (tuples of (RETAIN|ADD|REMOVE, text)), self.category_counts, start/len fields; appends human-readable problem strings.

### Decisive source
```python
# find_start_line: anchor by fuzzy match of first hunk line
pot_start_lines = {key: is_similar(self.lines[0][1], line) for key, line in lines_dict.items()}
sum_of_matches = sum(pot_start_lines.values())
if sum_of_matches == 0:
    if self.lines[0][1].count("#") > 0:
        self.relabel_line(0, ADD)          # LLM wrote a comment as context -> make it an ADD
        return self.validate_and_correct(lines_dict, problems)
    problems.append(f"...starting line ... does not exist in the code"); return False
elif sum_of_matches == 1:
    start_ind = <the matching key>          # unique anchor
else:
    logging.warning("multiple candidates for starting index")
    start_ind = <first matching key>        # ambiguous: pick first occurrence
```
```python
# validate_lines mismatch branch — three-way forward-block comparison
orig_count_ratio        = count_ratio(forward_block, forward_code)               # as-is
missing_line_count_ratio = count_ratio(lines_dict[file_ind] + forward_block_short, forward_code)  # skipped a line?
false_line_count_ratio  = count_ratio(forward_block_next, forward_code)          # invented a line?
if orig >= missing and orig >= false: problems.append(mismatch); return False
elif missing > false: self.add_retained_line(lines_dict[file_ind], hunk_ind); ...
else: self.pop_line(...)   # drop the invented line
```

**Flow:** check_start_line → find_start_line (fuzzy-anchor; comment-relabel escape hatch; leading-ADD handling searches first non-ADD line in file and PREPENDS the preceding retained line) → validate_lines walks hunk vs file: ADD skips, mismatch triggers the 3-way ratio vote (accept-with-problem vs insert-missing-line vs pop-false-line) → final partial-coverage check appends truncation problem.
**Invariant:** (1) `forward_block_len = 10` fixed lookahead; ratios compare SPACE-STIPPED lowercase character multisets. (2) Inserted retained lines go BEFORE the skipped block — deliberate documented choice ("IF IT MATTERED, WE ASSUME THE LLM WOULD NOT SKIP THE BLOCK"). (3) The `#`-heuristic fires twice independently (find_start_line zero-match and validate_lines mismatch): any line containing `#` suspected of being fake-context gets relabeled ADD. (4) After Diff-level correction, hunk_len_pre/post are RECOMPUTED from category_counts and start_line_post chained through previous hunk deltas — never trust the model's header numbers. (5) check_start_line's boolean is advisory only (its is_similar result is discarded); real gating lives in find_start_line.
**Probe:** `grep -c 'relabel_line' gpt_engineer/core/diff.py` → 3 (def :85 + two call sites :175/:213).
**Probe:** `grep -n 'forward_block_len = 10' gpt_engineer/core/diff.py` → :73.
**Probe:** `tests/core/test_chat_to_files.py::test_correct_skipped_lines` injects 4 comment lines mid-file and asserts the validator reproduces the stored corrected diff byte-for-byte.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "gpt-engineer", query: "find_start_line validate_lines relabel_line is_similar", limit: 10 });
```

## Verdict
Adopt the whole ladder — it is THE reusable asset for applying LLM unified diffs to drifted files; adapt threshold 0.9 and block length 10 to tolerance needs; omit Python-comment bias if targeting other languages (generalize the marker char). Tests: test_chat_to_files.py distortion cases are the behavioral spec.

<!-- capsule-v2 -->
# SEARCH/REPLACE — forgiving block matcher, loud failure loop, never silent fuzzy-apply

**Source:** Aider Apache-2.0 `main@5dc9490bb35f9729ef2c95d00a19ccd30c26339c`; Codebase Memory project `aider` (full index). **Question:** How does a harness apply model-authored SEARCH/REPLACE blocks without corrupting the file on a near-miss edit?

## Strict-match ladder and repair-failure loop
**Path/Symbol:** `aider/coders/editblock_coder.py`: `replace_most_similar_chunk(whole, part, replace)` (:157), `EditBlockCoder.apply_edits(edits, dry_run=False)` (:41), `do_replace(fname, content, before_text, after_text, fence)` (:364), `try_dotdotdots(...)` (:190).
**Signature:** edits are `(path, original, updated)` triples from fenced `<<<<<<< SEARCH / ======= / >>>>>>> REPLACE`; `apply_edits(...) -> None | raise ValueError`.
**Data Shape:** matched blocks apply immediately; failed blocks accumulate and a single `ValueError` returns both failures and successes; the fuzzy `replace_closest_edit_distance` sits below an unconditional `return` (dead code).

### Decisive source
```python
res = perfect_or_whitespace(whole_lines, part_lines, replace_lines)
if res:
    return res
if len(part_lines) > 2 and not part_lines[0].strip():
    res = perfect_or_whitespace(whole_lines, part_lines[1:], replace_lines)
    if res:
        return res
try:
    res = try_dotdotdots(whole, part, replace)
    if res:
        return res
except ValueError:
    pass
return  # <-- replace_closest_edit_distance below is DEAD CODE: a near miss must never silently edit the wrong lines
```

**Flow:** apply_edits iterates triples and matches per path; on a no-match with a non-empty original it retries that block against every other file in chat; passing edits write immediately; failures accumulate and a single `ValueError` returns failures+successes to constrain the retry.
**Invariant:** the fuzzy matcher is unreachable (`return` above it), so near misses always surface as repair feedback, never a guessed apply; the failure reply preserves the file's real text and a did-you-mean hint; a REPLACE already present triggers the double-apply guard; passed edits are excluded from the resend set.
**Probe:** `tests/basic/test_editblock.py::test_replace_part_with_missing_varied_leading_whitespace` (:240) uniform-indent recovery; `test_replace_part_with_missing_leading_whitespace_including_blank_line` (:309) dropped-blank+indent; `test_replace_multiple_matches` (:278) first-match-only.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "aider", query: "replace_most_similar_chunk apply_edits do_replace", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the strict-match-plus-smart-retry contract; port the matching ladder and failure loop as-is and keep any fuzzy matcher behind a disabled, non-default flag. Adapt the exact whitespace heuristics and error text to the host.

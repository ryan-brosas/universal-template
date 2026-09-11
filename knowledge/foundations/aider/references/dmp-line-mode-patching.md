<!-- capsule-v2 -->
# DMP line-mode patching — diff at line granularity with tight anchor knobs

**Source:** Aider Apache-2.0 `main@5dc9490bb35f9729ef2c95d00a19ccd30c26339c`; Codebase Memory project `aider` (full index). **Question:** Why does the last-resort edit strategy diff LINES instead of characters, and which diff_match_patch constants make that safe?

## linesToChars unitization + strict match settings
**Path/Symbol:** `aider/coders/search_replace.py`: `dmp_lines_apply(texts)` (:338), `lines_to_chars(lines, mapping)` (:329), `diff_lines(search_text, replace_text)` (:406).
**Signature:** `dmp_lines_apply -> str | None` (None = any patch failed to apply — all-or-nothing); asserts every input text ends with `\n`.
**Data Shape:** all three texts are concatenated ONCE and unitized together (`diff_linesToChars`) so a line maps to the same sentinel char everywhere; per-text slices are recovered by line counts; `Match_Threshold=0.1`, `Match_Distance=100_000`, `Match_MaxBits=32`, `Patch_Margin=1`.

### Decisive source
```python
all_text = search_text + replace_text + original_text
all_lines, _, mapping = dmp.diff_linesToChars(all_text, "")
assert len(all_lines) == len(all_text.splitlines())
...
new_lines, success = dmp.patch_apply(patches, original_lines)
new_text = lines_to_chars(new_lines, mapping)
all_success = False not in success
if not all_success:
    return            # partial application is failure, never returned
```

**Flow:** unitize → slice → diff_main on sentinel strings (cheap: operates on line-ids not text) → cleanupSemantic+Efficiency → patch_make → patch_apply against original-lines → rehydrate via mapping.
**Invariant:** the tight knobs are the safety story: 0.1 threshold means a patch anchors only within ~10% similarity of its expected location; Margin=1 keeps context minimal so hunks stay independent; shared unitization guarantees identical lines share sentinel ids across S/R/O — the precondition for correct cross-text patching. Contrast: the unused character-level `dmp_apply` (:260) uses LOOSE knobs (0.95/500/128/32) plus an offset-remapping pass (`map_patches`) — kept for benchmarking only.
**Probe:** executed this run: `.pi/work/foundations-deep-farm/scratch-aider-pass2/probe_gate5.py::flex-mangled-rescue` (line-mode DMP rescued a deep-indent-drifted edit through the strategy ladder), repo venv GREEN. No upstream direct tests.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "aider", name_pattern: "dmp_lines_apply", limit: 5 });
// also resolves: diff_lines, lines_to_chars (same file)
```

## Verdict
Adopt line-unitized DMP as the flexible-edit last resort WITH these exact knob semantics and all-or-nothing checking; adapt knob values only with your own corpus benchmarks; omit character-level `dmp_apply` + `map_patches` (benchmark-only path, documented trap: its offsets are wrong for drifted originals without remapping). Coverage caveat: probe-pinned only.

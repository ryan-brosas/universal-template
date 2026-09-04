<!-- capsule-v2 -->
# diff-apply-remove-flag — What is the two-phase line-edit algorithm behind apply_diffs?

**Source:** gpt-engineer MIT `main@a90fcd54`; Codebase Memory `gpt-engineer`. **Question:** How are adds/removes applied positionally without index corruption, and why the sentinel?

## Apply-diffs seam
**Path/Symbol:** `gpt_engineer/core/chat_to_files.py:apply_diffs` (:69-120).
**Signature:** `apply_diffs(diffs: Dict[str, Diff], files: FilesDict) -> FilesDict` (defensive copy: `FilesDict(files.copy())`).
**Data Shape:** Per file: OrderedDict{line_no: str}; sentinel `REMOVE_FLAG = "<REMOVE_LINE>"`; output rejoined with "\n".

### Decisive source
```python
REMOVE_FLAG = "<REMOVE_LINE>"  # Placeholder to mark lines for removal
...
current_line = hunk.start_line_pre_edit
for line in hunk.lines:
    if line[0] == RETAIN:  current_line += 1
    elif line[0] == ADD:
        current_line -= 1                       # insert AFTER current position
        if current_line in line_dict.keys() and line_dict[current_line] != REMOVE_FLAG:
            line_dict[current_line] += "\n" + line[1]   # append to existing line
        else:
            line_dict[current_line] = line[1]
        current_line += 1
    elif line[0] == REMOVE:
        line_dict[current_line] = REMOVE_FLAG   # defer deletion
        current_line += 1
line_dict = {k: line_content for k, line_content in line_dict.items() if REMOVE_FLAG not in line_content}
files[diff.filename_post] = "\n".join(line_dict.values())
```

**Flow:** mark phase walks each hunk mutating the ORIGINAL line numbering (retains advance, removes replace content with sentinel, adds splice after current line) → sweep phase filters any line CONTAINING the sentinel → join.
**Invariant:** (1) Adds DECREMENT then INCREMENT: an add following retain N lands BETWEEN N and N+1 by appending to line N with an embedded "\n" — this is why the filter checks substring containment (`REMOVE_FLAG not in c`), because appended content could theoretically sit on a sentinel-marked line otherwise. (2) Removals are deferred to the sweep — removing during the walk would shift every subsequent hunk index. (3) New-file diffs short-circuit: `"\n".join(line[1] for hunk ... for line in hunk.lines)` ignores headers entirely. (4) Renames work implicitly: patch applies to `filename_pre` content but stores under `filename_post` key. (5) Empty-file edge: `max(lines_dict)` would raise on empty dict — callers guarantee non-empty via validation phase.
**Probe:** `grep -n 'current_line -= 1' gpt_engineer/core/chat_to_files.py` → exactly one hit (:98) marking the insert-after decrement.
**Probe:** `grep -n 'if REMOVE_FLAG not in line_content' gpt_engineer/core/chat_to_files.py` → exactly one hit (:116), the sweep filter.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "gpt-engineer", query: "apply_diffs REMOVE_FLAG hunk start_line", limit: 10 });
```

## Verdict
Adopt mark-then-sweep with deferred removal for any positional line patcher; adapt sentinel uniqueness to your domain; omit rename-through-post-key if you reject renames. Behavioral spec: test_diff_changing_one_file / test_diff_adding_one_file round-trip diff_to_string equality.

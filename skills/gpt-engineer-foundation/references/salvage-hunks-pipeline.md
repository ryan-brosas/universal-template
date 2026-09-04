<!-- capsule-v2 -->
# salvage-hunks-pipeline — What survives when an LLM diff is partially wrong?

**Source:** gpt-engineer MIT `main@a90fcd54`; Codebase Memory `gpt-engineer`. **Question:** What is the exact validate→apply pipeline order, and which diffs are exempt from validation?

## Salvage pipeline seam
**Path/Symbol:** `gpt_engineer/core/default/steps.py:salvage_correct_hunks` (:341-360).
**Signature:** `salvage_correct_hunks(messages: List, files_dict: FilesDict, memory: BaseMemory, diff_timeout=3) -> tuple[FilesDict, List[str]]`.
**Data Shape:** Returns (patched FilesDict, residual error strings); logs transcripts to IMPROVE_LOG_FILE (`improve.txt`) and DIFF_LOG_FILE (`diff_errors.txt`) under `<project>/.gpteng/memory/logs/`.

### Decisive source
```python
error_messages = []
ai_response = messages[-1].content.strip()
diffs = parse_diffs(ai_response, diff_timeout=diff_timeout)
for _, diff in diffs.items():
    # if diff is a new file, validation and correction is unnecessary
    if not diff.is_new_file():
        problems = diff.validate_and_correct(file_to_lines_dict(files_dict[diff.filename_pre]))
        error_messages.extend(problems)
files_dict = apply_diffs(diffs, files_dict)
```

**Flow:** parse ALL diff blocks from last AI message (timeout-guarded) → per-diff: skip validation for NEW files (`filename_pre == "/dev/null"` or all-add hunks) else validate_and_correct against current file lines, collecting problem strings → apply EVERYTHING (valid hunks applied, invalid hunks were dropped inside Diff.validate_and_correct via `self.hunks.remove(hunk)`) → log both artifacts.
**Invariant:** (1) Validation MUTATES hunks (repairs) before application — apply_diffs receives corrected hunks, not raw ones. (2) New files bypass validation entirely: any content the model emits becomes the file. (3) Partial success is the norm: hunks removed for failure do not abort sibling hunks; the returned error list tells the caller whether a refinement round is worthwhile. (4) `Diff.validate_and_correct` cuts the searchable window after each hunk (`cut_ind = min(past.end_pre, next.start_pre)`) so later hunks cannot anchor into earlier regions — positional safety comes from monotone window shrinking.
**Probe:** `grep -n 'is_new_file()' gpt_engineer/core/default/steps.py` → single exemption site :352.
**Probe:** `tests/core/test_salvage_correct_hunks.py` runs REAL captured failure chats (task_master, wheaties, vgvishesh, apps_benchmark_6) through this function — golden corpus for the salvage contract.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "gpt-engineer", query: "salvage_correct_hunks validate_and_correct apply_diffs parse_diffs", limit: 10 });
```

## Verdict
Adopt validate-mutate-then-apply ordering and the new-file exemption; adapt error taxonomy strings; omit the log filenames. The salvage test corpus is the fastest way to regression-test a ported validator — carry it.

<!-- capsule-v2 -->
# replace_file_str missing-text guard — what happens when old_str is absent?

**Source:** browser-use MIT `main@85ddbfedf609166b2d2c76c3d80506649fee82a9`; Codebase Memory `mnt-hdd-utopia-inspo-agents-browser-use`. **Question:** when the search text does not exist in the file, should replace rewrite the file or report an error — and what changed upstream in #5498?

## Missing-text early return (added upstream 2026-08-18)
**Path/Symbol:** `browser_use/filesystem/file_system.py:776-804` (`FileSystem.replace_file_str`; the guard is :795-796).
**Signature:** `async def replace_file_str(self, full_filename: str, old_str: str, new_str: str) -> str`.
**Data Shape:** returns human-readable status strings (never raises for expected failures); reads/writes through the in-memory `BaseFile` object and syncs to `self.data_dir`.

### Decisive source
```python
content = file_obj.read()
if old_str not in content:                                    # ← added by 3648bba/85ddbfe (#5498)
    return f'Error: Could not find the specified text in file {full_filename}.'
content = content.replace(old_str, new_str)
await file_obj.write(content, self.data_dir)                  # full-file rewrite, not in-place patch
return f'Successfully replaced all occurrences of "{old_str}" with "{new_str}" in file {full_filename}{sanitize_note}'
```

**Flow:** resolve/sanitize filename → reject empty `old_str` (:784-785) → look up in-memory file object → read content → **NEW: membership check before any mutation** → `str.replace` ALL occurrences → write whole content back to disk → success string includes auto-corrected filename note when sanitization fired.
**Invariant:** a failed replace must leave BOTH the in-memory object and the on-disk bytes untouched — before this guard, absent text silently produced a no-op *rewrite* that reported success ("Successfully replaced…"), so agents could believe a todo item was checked off when nothing happened. Error strings are model-facing data (the tool layer surfaces them verbatim), not exceptions.
**Probe:** `tests/ci/infrastructure/test_filesystem.py::test_replace_file_reports_missing_text` (:481) — asserts result equals `'Error: Could not find the specified text in file todo.md.'` AND `fs.get_file('todo.md').content == original_content` AND the disk file still holds the original bytes.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-browser-use", query: "replace_file_str old_str not in content", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the membership-check-before-write guard verbatim (it converts a silent lie into a truthful error). Adapt the message wording to your host's error convention. Omit nothing else — the empty-string rejection (:784) and sanitized-name notes are part of the same contract.

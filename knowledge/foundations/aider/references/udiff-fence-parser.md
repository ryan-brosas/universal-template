<!-- capsule-v2 -->
# udiff fence parser — ```diff blocks, path carry-forward, a/ b/ prefix stripping

**Source:** Aider Apache-2.0 `main@5dc9490bb35f9729ef2c95d00a19ccd30c26339c`; Codebase Memory project `aider` (full index). **Question:** How do you extract per-file unified-diff hunks from free-form LLM markdown where paths appear only once for many hunks?

## Fence scan with sticky path
**Path/Symbol:** `aider/coders/udiff_coder.py`: `find_diffs(content)` (:312), `process_fenced_block(lines, start_line_num)` (:337).
**Signature:** `find_diffs -> list[(path|None, hunk_lines)]`; inside `get_edits`, a None path inherits `last_path` (sticky across hunks).
**Data Shape:** fences open with ```` ```diff ```` and close at the next ```` ``` ````; a synthetic `"@@ @@"` is appended to the block so the trailing hunk always flushes; git-style headers are normalized (`a/…`/`b/…` prefixes stripped; `/dev/null` on the A-side tolerated).

### Decisive source
```python
if block[0].startswith("--- ") and block[1].startswith("+++ "):
    a_fname = block[0][4:].strip()
    b_fname = block[1][4:].strip()
    if (a_fname.startswith("a/") or a_fname == "/dev/null") and b_fname.startswith("b/"):
        fname = b_fname[2:]
    else:
        fname = b_fname          # assume the path is as intended
    block = block[2:]            # headers consumed; subsequent +++ flips current path mid-fence
```
Hunk flush rule: an `+++ ` line immediately after a `--- ` line REBINDS the path (multi-file fence); otherwise hunks flush at `@@` lines — but only if the hunk contains at least one `-`/`+` op (`keeper` flag), so context-only noise never becomes an edit.

**Flow:** scan for ```` ```diff ```` → process fenced block → hunks accumulate as `(fname, hunk)`; `get_edits` then back-fills None paths from the previous hunk's path.
**Invariant:** a hunk with zero change-ops is discarded (keeper gate); path binding follows the LAST seen header pair; unterminated final fence still yields its hunks thanks to the appended sentinel `@@ @@`.
**Probe:** `tests/basic/test_udiff.py::test_find_diffs_single_hunk` (:8), `::test_find_multi_diffs` (:71 multi-hunk), `::test_find_diffs_dev_null` (:29), `::test_find_diffs_dirname_with_spaces` (:50) — direct upstream suite, all four pin this parser.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "aider", name_pattern: "find_diffs", limit: 5 });
// also resolves: process_fenced_block (same file)
```

## Verdict
Adopt the sticky-path + keeper-gate + sentinel-flush grammar as-is; adapt fence markers to your host's conventions; omit nothing — the whole file is 90 lines of load-bearing parsing. Direct-test coverage exists for parsing only.

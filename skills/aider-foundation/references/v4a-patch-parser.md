<!-- capsule-v2 -->
# V4A patch parser — sentinel-tolerant Begin Patch, action merge rules, EOF marker, fuzz accounting

**Source:** Aider Apache-2.0 `main@5dc9490bb35f9729ef2c95d00a19ccd30c26339c`; Codebase Memory project `aider` (full index). **Question:** How do you parse the GPT-4.1-style `*** Begin Patch` format (Add/Update/Delete/Move) so that malformed model output fails loudly instead of half-applying?

## Sentinel tolerance + action table
**Path/Symbol:** `aider/coders/patch_coder.py`: `PatchCoder.get_edits()` (:220), `_parse_patch_text(lines, start_index, current_files)` (:290), `_parse_add_file_content(lines, index)` (:516), `identify_files_needed(text)` (:194), domain objects `DiffError` :13 / `ActionType` :17 / `Chunk` :23 / `PatchAction` :30 / `Patch.fuzz` :46.
**Signature:** `get_edits() -> list[(path, PatchAction)]`; every structural violation raises `DiffError` (a ValueError), which get_edits re-raises as ValueError with context.
**Data Shape:** sentinels: `*** Begin Patch` header (tolerated missing if any line starts with `@@`/`*** Update File:`/`*** Add File:`/`*** Delete File:` — then warn + parse anyway, `start_index=0`); actions keyed by path in a dict; duplicate UPDATE blocks MERGE (chunks.extend + move-target conflict check), duplicate DELETE warns-and-ignores, ADD-after-anything and DELETE-after-ADD raise Conflicting.

### Decisive source
```python
if (
    len(lines) < 2
    or not _norm(lines[0]).startswith("*** Begin Patch")
):
    is_patch_like = any(
        _norm(line).startswith(("@@", "*** Update File:", "*** Add File:", "*** Delete File:"))
        for line in lines
    )
    if not is_patch_like:
        self.io.tool_warning("Response does not appear to be in patch format.")
        return []                       # not-a-patch ⇒ empty edit set, no exception
    self.io.tool_warning("Patch format warning: Missing '*** Begin Patch'/'*** End Patch' sentinels.")
    start_index = 0                     # patch-like ⇒ proceed WITHOUT the header
```
Pre-parse file staging: `identify_files_needed` extracts Update/Delete paths FIRST; unreadable path ⇒ `DiffError(f"File referenced in patch not found: ...")` BEFORE any parsing — parse-time context lookups never hit the filesystem mid-stream.

**Flow:** strip CR (`_norm`) everywhere so CRLF input parses like LF → walk actions → per-file sections parsed by `_parse_update_file_sections` (see its capsule) → accumulate `patch.fuzz` across all fuzzy matches → tolerate missing `*** End Patch`.
**Invariant:** unknown top-level lines raise `Unknown or misplaced line`; blank lines between actions are legal separators only; Add content lines MUST start with `+` except blank lines (which add empty lines); Move targets must agree across merged blocks.
**Probe:** no upstream test suite for this module → executed this run: `.pi/work/foundations-deep-farm/scratch-aider-pass2/probe_gate5.py::patch-peek-section` (chunk boundaries + orig_index derivation) — parser internals exercised at source level; full-sentinel behavior pinned by source reading only. Coverage caveat recorded.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "aider", name_pattern: "peek_next_section", limit: 5 });
// also resolves: identify_files_needed, PatchAction, DiffError (same file)
```

## Verdict
Adopt the three-way behavior split for malformed input (not-patch⇒empty+warn / patch-like-without-sentinels⇒proceed+warn / structural garbage⇒raise) and the action merge matrix; adapt sentinel strings to your dialect; omit the reference-script provenance comments. Coverage caveat: zero direct tests upstream; probe-pinned.

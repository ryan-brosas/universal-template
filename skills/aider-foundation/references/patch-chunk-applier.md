<!-- capsule-v2 -->
# Patch chunk application — index-absolute chunks, delete-line verification, move-after-write

**Source:** Aider Apache-2.0 `main@5dc9490bb35f9729ef2c95d00a19ccd30c26339c`; Codebase Memory project `aider` (full index). **Question:** Once a patch is parsed into indexed chunks, how do you rebuild the file so overlapping or drifted chunks fail instead of corrupting?

## Sorted sequential splice with double-check
**Path/Symbol:** `aider/coders/patch_coder.py`: `PatchCoder._apply_update(text, action, path)` (:642), `apply_edits(edits)` (:549), `Chunk.orig_index` (:24).
**Signature:** `_apply_update -> str` with single trailing newline; raises DiffError on overlap/mismatch.
**Data Shape:** chunk `orig_index` is ABSOLUTE (parser adds the matched context's file offset); chunks sorted by orig_index then applied left-to-right; between-chunk original lines are copied verbatim; each chunk's `del_lines` are re-verified against the actual file slice under `.strip()`-normalization before insertion.

### Decisive source
```python
if chunk_start_index < current_orig_line_idx:
    raise DiffError(f"{path}: Overlapping or out-of-order chunk detected. ...")
dest_lines.extend(orig_lines[current_orig_line_idx:chunk_start_index])
actual_deleted_lines = orig_lines[chunk_start_index : chunk_start_index + num_del]
norm_chunk_del  = [_norm(s).strip() for s in chunk.del_lines]
norm_actual_del = [_norm(s).strip() for s in actual_deleted_lines]
if norm_chunk_del != norm_actual_del:
    raise DiffError(
        f"{path}: Mismatch applying patch near line {chunk_start_index + 1}.\n"
        f"Expected lines to remove:\n{expected_str}\nFound lines in file:\n{actual_str}")
```
Move semantics in `apply_edits`: write new content to `move_path` FIRST, `unlink()` the original only AFTER a successful write (`if action.move_path and full_path != target_full_path: path_obj.unlink()`), warning (not raising) when an existing move target gets overwritten.

**Flow:** ADD ⇒ existence check then mkdir-parents + ensure-trailing-newline; DELETE ⇒ missing file warns-and-skips (idempotent), else unlink; UPDATE ⇒ re-read file, `_apply_update`, optional move-then-delete; every caught exception class re-raises as ValueError naming action type and path.
**Invariant:** the parser's context match is NEVER trusted at apply time — del-lines are verified against real bytes again; overlap/out-of-order is a hard error, not a silent merge; trailing newline normalized to exactly one unless both result and original were empty.
**Probe:** executed this run: `.pi/work/foundations-deep-farm/scratch-aider-pass2/probe_gate5.py::patch-update-apply` (happy-path splice AND loud "Mismatch applying patch near line 3"), repo venv GREEN. No upstream direct tests.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "aider", name_pattern: "_apply_update", limit: 5 });
// resolves: aider.aider.coders.patch_coder.PatchCoder._apply_update
```

## Verdict
Adopt verify-at-apply + sorted-splice + move-after-write verbatim; adapt error message formats; omit nothing — this is the safety kernel of the V4A coder. Coverage caveat: probe-pinned only.

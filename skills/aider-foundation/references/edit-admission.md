<!-- capsule-v2 -->
# Edit admission — dispatch by registered format and gate every file-scope expansion

**Source:** Aider Apache-2.0 `main@5dc9490bb35f9729ef2c95d00a19ccd30c26339c`; Codebase Memory project `aider`. **Question:** How does a harness change edit protocols without corrupting the transcript, and prevent model output from silently widening the writable file set?

## Format dispatch and target admission
**Path/Symbol:** `aider/coders/base_coder.py`: `Coder.create(...)` (:85-159), `Coder.allowed_to_edit(path)` (:2191-2240), `prepare_to_edit(edits)` (:2269-2294).
**Signature:** `Coder.create(main_model=None, edit_format=None, io=None, from_coder=None, summarize_from_coder=True, **kwargs) -> Coder`; `allowed_to_edit(path) -> bool`.
**Data Shape:** requested or inherited `edit_format`; prior coder transcript and file set; writable `abs_fnames`; Git-ignore and dirty-baseline status for a proposed target path.

### Decisive source
```python
if edit_format != from_coder.edit_format and done_messages and summarize_from_coder:
    done_messages = from_coder.summarizer.summarize_all(done_messages)
for coder in coders.__all__:
    if hasattr(coder, "edit_format") and coder.edit_format == edit_format:
        return coder(main_model, io, **kwargs)
raise UnknownEditFormat(edit_format, valid_formats)
...
if self.repo and self.repo.git_ignored_file(path):
    self.io.tool_warning(f"Skipping edits to {path} that matches gitignore spec.")
    return
if not self.io.confirm_ask("Allow edits to file that has not been added to the chat?", subject=path):
    return
self.abs_fnames.add(full_path)
self.check_for_dirty_commit(path)
```

**Flow:** resolve the requested format from explicit input, prior coder, or model default; summarize old assistant messages only when a format switch would make them misleading; dispatch only through the registered format registry; raise `UnknownEditFormat` for anything unregistered. For each proposed edit, allow in-chat targets, reject gitignored paths, and require per-file consent before admitting a new editable file; snapshot already-dirty baselines before editing.

**Invariant:** a format switch never carries incompatible assistant-format examples into the next model call. The model cannot widen edit scope to a gitignored or unapproved path.

**Probe:** `tests/basic/test_coder.py::test_unknown_edit_format_creation` (:1047-1058) requires a raise for an unregistered format; `test_allowed_to_edit`, `test_allowed_to_edit_no`, and `test_allowed_to_edit_dirty` (:25-102) cover approved, rejected, and dirty targets.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "aider", query: "Coder.create allowed_to_edit prepare_to_edit UnknownEditFormat", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt registered-format dispatch, transcript sanitation on a protocol change, and explicit writable-set expansion; adapt the specific coder registry and summarizer; omit Aider-specific format names.

<!-- capsule-v2 -->
# Filename sanitize-then-resolve ladder — how do you accept messy LLM filenames without traversal?

**Source:** browser-use MIT `main@85ddbfedf609166b2d2c76c3d80506649fee82a9`; Codebase Memory `mnt-hdd-utopia-inspo-agents-browser-use`. **Question:** how does the filesystem accept `My File!.md` and `../secret.md` while keeping writes inside its data dir?

## Validate → sanitize → re-validate, basename-first
**Path/Symbol:** `browser_use/filesystem/file_system.py:407-475` (`_is_valid_filename` :407, `sanitize_filename` :423, `_resolve_filename` :451; error-message builder :40).
**Signature:** `_resolve_filename(file_name: str) -> tuple[str, bool]` returning `(resolved_name, was_sanitized)`; every public op (`get_file`/`display_file`/`read_file*`/`write_file`/`append_file`/`replace_file_str`) calls it first.
**Data Shape:** regex allow-list `^[a-zA-Z0-9_\-\.\(\) \u4e00-\u9fff]+\.(md|txt|json|jsonl|csv|pdf|docx|html|xml)$`; non-empty name part required before the last dot; extension matched case-sensitively at validation but lowercased by sanitization.

### Decisive source
```python
def _resolve_filename(self, file_name: str) -> tuple[str, bool]:
    base_name = os.path.basename(file_name)          # normalize FIRST → kills ../secret.md
    was_changed = base_name != file_name             # any path component ⇒ was_changed=True
    if self._is_valid_filename(base_name):
        return base_name, was_changed
    sanitized = self.sanitize_filename(base_name)
    if sanitized != base_name and self._is_valid_filename(sanitized):
        return sanitized, True                       # auto-corrected name wins
    return base_name, was_changed                    # unresolvable → caller reports specific error
```

**Flow:** take basename (directory traversal dies here) → validate against the allow-list regex → on failure, sanitize (spaces→hyphens, strip disallowed chars keeping CJK + parens, collapse hyphens, strip edge hyphens/dots, fallback name `'file'`, lowercase extension) → re-validate → return with a flag. Callers append `(auto-corrected from '<original>')` notes to success strings and "not found (auto-corrected…)" to misses so the model learns what happened.
**Invariant:** files are ALWAYS keyed by resolved full filename in one `{full_name -> BaseFile}` dict — resolution happens exactly once per operation before lookup/store, so `my file.md`, `My File!.md`, and `my-file.md` converge on one entry; an unsanitizable name never reaches the store (specific error via `_build_filename_error_message`, which distinguishes binary-extension / unsupported-extension / no-extension / invalid-chars cases).
**Probe:** `tests/ci/infrastructure/test_filesystem.py::TestFilenameSanitization::test_path_traversal_prevented` (:1179) — writes `'../secret.md'`, asserts storage under basename INSIDE data_dir, parent dir clean, nested `'../../etc/passwd.txt'` also stripped; the whole 19-test class (:957-1216) pins each rule incl. `test_replace_file_with_sanitized_name` (:1108).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-browser-use", query: "_resolve_filename _is_valid_filename sanitize_filename", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt basename-first resolution plus sanitize-and-revalidate with the was_sanitized flag — it is the whole safety story for model-supplied filenames. Adapt the character allow-list (CJK range is a product choice). Omit nothing: skipping the flag loses the user-visible correction note that keeps agents from re-using dead names.

<!-- capsule-v2 -->
# Filesystem path-leak sanitization + TOCTTOU resolve-before-authorize ordering

## Source / Question
`pydantic_ai_harness/filesystem/_toolset.py:50–115, 168–320` @ `main@f971198` — Two porting traps in one sandboxed filetool: (a) OS error messages embed absolute host paths that must never reach the model; (b) pattern authorization done on unresolved paths is bypassable by symlinks and `.`/`..` segments. What is the correct ORDER and redaction contract?

## Path / Symbol
`filesystem/_toolset.py` — `_OUTSIDE_WORKSPACE='<outside-workspace>'` / `_NOT_A_PATH='<not-a-path>'` sentinels (:50–54), `_model_safe_filename` (:57–77), `_sanitize_recoverable_error` (:80–91), `_resolve_path` (:228–251), `_check_access(check_allowed=)` (:253–275), `_resolve_walk_entry` (:290–304), `_safe_resolve` (:310–320).

## Signature
```python
def _sanitize_recoverable_error(error: BaseException, real_root: Path) -> str:
    if not isinstance(error, OSError) or error.filename is None:
        return str(error)
    filename = _model_safe_filename(error.filename, real_root)
    return f'[Errno {error.errno}] {error.strerror}: {filename!r}'   # path RELATIVE or sentinel

def _safe_resolve(self, path: str, *, write=False, check_allowed=True) -> Path:
    resolved = self._resolve_path(path)                              # realpath FIRST
    self._check_access(self._relative_to_root(resolved), ...)        # patterns against CANONICAL rel path
```

## Data Shape
Redaction ladder in `_model_safe_filename`: relative paths pass through; absolute-under-root become root-relative; realpath'd symlink aliases normalized under root (macOS `/var`→`/private/var`); outside-root ⇒ `<outside-workspace>`; non-path values ⇒ `<not-a-path>`.

### Decisive source
Ordering comment (:311–317): "Resolution happens first so the access check matches patterns against the canonical path relative to the root, collapsing `.`/`..`/`//` segments that would otherwise slip past a literal pattern (e.g. `config/./secret.txt` evading a `config/secret.txt` deny rule)." Walkers authorize each entry ONCE at its realpath then do I/O on that same returned path (:290–298): "the path that was authorized is the path that gets read." Walkers skip `allowed_patterns` for their ROOT directory but filter entries per-entry (`check_allowed=False` + `_resolve_walk_entry`) because `.` never matches a file glob (:494–496, :544–545). Protected patterns gate WRITES only — reads of `.env` stay visible (:262–266).

**Flow:** raw path → realpath+loop-probe → containment check against `self._real_root` → pattern check on canonical relative path → I/O.
**Invariant:** no absolute host path may appear in any ModelRetry/tool message; a symlink can neither escape the root nor alias past a rule its own name would trip.

## Probe (direct test)
`tests/filesystem/test_filesystem.py::TestModelSafeRecoverableErrors` (:1770+) — `test_outside_root_path_is_redacted` (`str(outside) not in message`, `<outside-workspace>` present :1783), `test_relative_filename_is_preserved`, `test_non_path_filename_is_labeled`, `test_symlink_alias_is_normalized`; `test_traversal_absolute_path` :130, `test_symlink_escape` :138, `test_list_skips_dangling_symlink` :634, `test_find_absolute_pattern_rejected` :968.

## Retrieve
```
search_graph --project pydantic-ai-harness --name-pattern '_model_safe_filename _safe_resolve _resolve_walk_entry'
```

## Verdict
**Adopt** resolve-before-authorize + sentinel redaction verbatim for any sandboxed file tool. **Adapt** the protected-pattern policy to your threat model. **Omit** nothing.

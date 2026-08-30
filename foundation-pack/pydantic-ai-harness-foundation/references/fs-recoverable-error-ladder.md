<!-- capsule-v2 -->
# Filesystem recoverable-error ladder: model-correctable tool failures become ModelRetry, everything else aborts

## Source / Question
`pydantic_ai_harness/filesystem/_toolset.py:1–115` @ `main@f971198` — pydantic-ai feeds ONLY `ModelRetry` back to the model; any other exception ends the whole run. Which filesystem failures mean "the model asked for something fixable" and how do you classify them without accidentally retrying ENOSPC?

## Path / Symbol
`filesystem/_toolset.py` — `_RECOVERABLE_ERRORS` tuple (:31), `_RECOVERABLE_ERRNOS` dict (:43–47), `_WINDOWS_ERROR_INVALID_NAME = 123` (:48), `_recoverable` decorator (:94–115); applied to all eight tools.

## Signature
```python
_RECOVERABLE_ERRORS = (PermissionError, FileNotFoundError, NotADirectoryError, IsADirectoryError, ValueError)
_RECOVERABLE_ERRNOS: dict[int | None, str] = {
    errno.ENAMETOOLONG: 'The path name is too long.',
    errno.ELOOP: 'The path resolves through a symlink loop.',
    errno.EILSEQ: 'The path name contains a byte sequence the filesystem cannot represent.',
}
@_recoverable
async def fn(...) -> str   # wraps every tool; OSError falls through unless errno is in the table
```

## Data Shape
Two tiers: dedicated exception subclasses (broad), then bare `OSError`s classified by EXPLICIT errno allowlist — "Entries are explicit so other errors keep aborting the run; for example, retrying cannot fix `ENOSPC` or `EROFS`" (:33–36). Windows winerror 123 (INVALID_NAME) maps to the same family (:108–109).

### Decisive source
```python
except _RECOVERABLE_ERRORS as e:
    real_root = self._real_root
    raise ModelRetry(_sanitize_recoverable_error(e, real_root)) from e
except OSError as e:
    reason = _RECOVERABLE_ERRNOS.get(e.errno)
    if reason is None and getattr(e, 'winerror', None) == _WINDOWS_ERROR_INVALID_NAME:
        reason = 'The path name is invalid.'
    if reason is None:
        raise                      # NOT a retry — run dies
    raise ModelRetry(reason) from e
```
Version-dependent surface documented in-source (:37–40): `Path.is_file` stopped propagating `ENAMETOOLONG` in 3.14, so on 3.10–3.13 read ops surface it via the tuple tier while the write path reaches it via the errno tier. Symlink loops arrive differently per Python (`RuntimeError` 3.10–3.12 vs suppressed `ELOOP` 3.13+) and are ALSO handled inside `_resolve_path` (:228–247).

**Flow:** tool body raises → subclass tier converts with sanitized message → bare-OSError tier consults errno table → unknown errno re-raises to abort.
**Invariant:** fail-loud for non-model-fixable errors; every converted message must be path-free (see fs-path-leak-sanitization capsule).

## Probe (direct test)
`tests/filesystem/test_filesystem.py::test_symlink_loop_is_recoverable` (:1069), `test_real_symlink_loop_is_reported` (:1082), `test_write_through_symlink_loop` (:1133); FIFO/regular-file classification tests :370–428; `find_files` NotImplementedError branch documents why neither tier can catch rooted-glob rejection (:610–619).

## Retrieve
```
search_graph --project pydantic-ai-harness --name-pattern '_recoverable _sanitize_recoverable_error' --detail ids
```

## Verdict
**Adopt** the two-tier ladder (subclass whitelist + explicit-errno table) for any agent-facing OS-touching toolset. **Adapt** the errno table to your syscall surface. **Omit** the Windows branch only if POSIX-only.

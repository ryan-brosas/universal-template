<!-- capsule-v2 -->
# Overflow store hardening: 0700 root, escape-proof handles, off-hot-path TTL pruning

## Source / Question
`pydantic_ai_harness/tool_output_limits/_store.py` — When spilled payloads live in a SHARED, stable directory (a later run may read a spill a previous run produced), how do you make path-addressable handles safe without per-instance isolation? Porters either isolate per-run (breaking cross-run reads) or accept traversal/symlink escapes into the store.

## Path / Symbol
`tool_output_limits/_store.py` — `OverflowStore` protocol (:24–42), `_safe_segment` (:45–57), `LocalFileStore.__post_init__`/`_path` (:92–101), `read` resolve check (:119–124), prune family (:128–153).

## Signature
```python
def read(self, handle: str) -> bytes:
    target = self._path(handle).resolve()      # FOLLOWS symlinks
    root   = self._root.resolve()
    if not target.is_relative_to(root):
        raise PermissionError(f'Handle {handle!r} resolves outside the store root.')
    return target.read_bytes()

_UNSAFE_SEGMENT = re.compile(r'[^A-Za-z0-9._-]+')
def _safe_segment(segment):                    # '' / '.' / '..' -> '_'
```

## Data Shape
Handle == key: a relative `run/call.retry` path under `base_dir` (default `<tmp>/pyai_harness_overflow`). Root created with parents + chmod 0700 (best-effort). Files kept after the run by default; `cleanup_after: timedelta | None` opts into age-based pruning.

### Decisive source
1. **Shared-by-design root** (:63–75 docstring): "The root is stable and shareable on purpose — a later agent or run can read a spill a previous run produced, so the store is not isolated per instance. Security comes from two mechanisms, not isolation": 0700 perms AND resolve-within-root rejection.
2. **Two-line defense** (`_safe_segment` :48–57): sanitization makes escapes unrepresentable ("a handle can never escape the root via `.`/`..`"); the resolve check is "the second line of defense" against symlink swaps between write and read.
3. **st_mtime, never st_atime** (:81–87): pruning keys on modification time because "last-read time is unreliable on noatime/relatime mounts."
4. **Prune is off the hot path and cannot fail the run**: daemon thread per write when enabled; any exception → `warnings.warn`, never propagation (:136–140); per-file OSError swallowed (vanished mid-prune).

## Flow / Invariant
write: ensure root → sanitize segments → write bytes → schedule optional prune → return key as handle. read: sanitize → resolve → containment assert → read bytes. Invariants: no handle string can produce a path outside the root even under adversarial input; cleanup failure never blocks or fails an agent run.

## Probe (direct test)
`tests/tool_output_limits/test_tool_output_limits.py::TestStore`: `test_root_created_0700` (:207), `test_empty_key` (:213), `test_dotdot_handle_stays_in_root` (:223), `test_symlink_escape_rejected` (:231), `test_read_missing_raises` (:218). `TestCleanup`: `test_prune_removes_old_keeps_new` (:248), `test_run_prune_swallows_errors` (:263), `test_schedule_none_when_disabled` (:273).

## Retrieve
`search_graph --project pydantic-ai-harness --query 'LocalFileStore _safe_segment OverflowStore prune cleanup_after'`

## Verdict
**Adopt** the two-mechanism pattern (segment sanitization + resolved containment) for ANY user/model-influenced path under a shared root. **Adopt** daemon-thread best-effort TTL pruning that warns instead of raising. **Adapt** the backend — the protocol is just `write(key, data) -> handle` / `read(handle) -> bytes`.

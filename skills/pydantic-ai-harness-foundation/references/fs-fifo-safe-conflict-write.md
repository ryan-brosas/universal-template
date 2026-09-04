<!-- capsule-v2 -->
# FIFO-hardened optimistic-concurrency write: classify the descriptor before any byte moves

## Source / Question
`pydantic_ai_harness/filesystem/_toolset.py:354–437` @ `main@f971198` (PR #613/#628) — How do you write a file that a hostile/concurrent actor may swap for a FIFO or symlink BETWEEN authorization and open, without blocking forever on a FIFO, following a symlink, or clobbering content whose hash the caller pinned?

## Path / Symbol
`filesystem/_toolset.py` — `write_file(path, content, *, expected_hash=None)` (:355–437); platform flags :382; 3× open-retry loop :390–402; fstat classification :413; hash-check-then-truncate :420–430.

## Signature
```python
async def write_file(self, path: str, content: str, *, expected_hash: str | None = None) -> str
platform_flags = os.O_BINARY if os.name == 'nt' else os.O_NONBLOCK | os.O_NOFOLLOW
access_flags   = os.O_RDWR if expected_hash is not None else os.O_WRONLY
```

## Data Shape
`expected_hash` = sha256-prefix (`_content_hash`, first 12 hex of full text) returned by earlier read/write calls — the optimistic-concurrency token. Returns confirmation carrying the NEW hash.

### Decisive source
```python
# Opening without O_TRUNC lets us classify the descriptor and check the
# expected hash before changing the file. POSIX non-blocking mode keeps
# a FIFO swapped into place from waiting for a reader; O_NOFOLLOW keeps
# a final-component symlink swap from redirecting the descriptor. (:376–381)
for _ in range(3):                                   # target can vanish after O_EXCL says it exists
    try:    descriptor = os.open(resolved, access|platform|O_CREAT|O_EXCL, 0o666)
    except FileExistsError:
        try:    descriptor = os.open(resolved, access|platform)
        except FileNotFoundError: continue             # re-run FULL classification
    else:   created = True
    break
else: raise ModelRetry(f'Path {path!r} changed repeatedly while opening. Retry the write.')
...
if not stat.S_ISREG(os.fstat(descriptor).st_mode):   # FIFO/dir/device ⇒ ModelRetry, never a hang
    raise ModelRetry(f'Path {path!r} exists and is not a regular file.')
mode = 'r+' if expected_hash is not None else 'w'    # r+: READ-hash BEFORE truncate
with text_file:
    if expected_hash is not None and not created:
        current = _content_hash(text_file.read())    # compare on the OPEN DESCRIPTOR
        if current != expected_hash: raise ValueError('Conflict: … Re-read the file and retry.')
    text_file.seek(0); text_file.truncate(0); text_file.write(content)
```

**Flow:** pre-checks → O_EXCL create → exists ⇒ reopen without O_TRUNC → ELOOP/EISDIR/ENODEV/ENXIO map to ModelRetry (:403–410) → fstat S_ISREG gate → optional descriptor-level hash check → only then truncate+write.
**Invariant:** no `O_TRUNC` until classification AND conflict check pass; a swapped-in FIFO must hit `S_ISREG` fail (O_NONBLOCK) rather than block; a swapped symlink hits `O_NOFOLLOW`/ELOOP; the swap-window is bounded at 3 attempts then a loud ModelRetry.

## Probe (direct test)
`tests/filesystem/test_filesystem.py::test_write_existing_fifo_retries_without_blocking` (:370, SIGALRM fires if write blocks), `test_write_rejects_fifo_swapped_before_descriptor_open` (:393, monkeypatched os.open swaps mid-call, asserts `flags & os.O_NONBLOCK`, both with/without reader), `test_write_expected_hash_checks_swapped_target` (:514, file replaced between check and open ⇒ Conflict + replacement intact), `test_write_rejects_symlink_swapped_before_descriptor_open` (:540, `flags & os.O_NOFOLLOW`, sibling file untouched), `test_write_conflict_detection/rejection` (:501/:510), `test_write_overwrite_preserves_permissions` (:488).

## Retrieve
```
search_graph --project pydantic-ai-harness --name-pattern 'write_file expected_hash' --detail ids
# symbol: pydantic_ai_harness.filesystem._toolset.FileSystemToolset.write_file
```

## Verdict
**Adopt** the no-O_TRUNC-descriptor-classification pattern anywhere tool writes meet untrusted paths. **Adapt** retry bound and flag set per platform. **Omit** nothing.

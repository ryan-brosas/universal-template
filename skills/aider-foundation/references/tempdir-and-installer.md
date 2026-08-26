<!-- capsule-v2 -->
# Cleanup-tolerant temp dirs + consent-gated pip install — test-infra wrappers that survive locked Windows files

**Source:** Aider Apache-2.0 `main@5dc9490bb35f9729ef2c95d00a19ccd30c26339c`; Codebase Memory project `aider` (full index). **Question:** How do you build throwaway git repos/chdirs for tests and self-install optional dependencies without the cleanup or install ever crashing the host?

## Wrapper ladder + import-probe-install loop
**Path/Symbol:** `aider/utils.py`: `IgnorantTemporaryDirectory` (:16), `ChdirTemporaryDirectory` (:39), `GitTemporaryDirectory` (:62), `make_repo(path)` (:73), `check_pip_install_extra(io, module, prompt, pip_install_cmd, self_update=False)` (:298), `run_install(cmd)` (:213), `find_common_root(abs_fnames)` (:263).
**Signature:** context managers; `check_pip_install_extra -> True | None`; `find_common_root -> str` never raises even when cwd was deleted.
**Data Shape:** cleanup swallows `(OSError, PermissionError, RecursionError)` (Windows file locks + GC recursion); chdir wrapper remembers cwd BEFORE entering and restores it on exit tolerating `FileNotFoundError` if the old cwd vanished; Git wrapper deletes its repo object before super-exit so handles close in order.

### Decisive source
```python
def cleanup(self):
    try:
        self.temp_dir.cleanup()
    except (OSError, PermissionError, RecursionError):
        pass  # Ignore errors (Windows and potential recursion)
```
Install flow: probe `__import__(module)` first (already present ⇒ return True) → warn with prompt → Windows + self_update ⇒ print manual command and STOP (never self-update a running exe) → `confirm_ask("Run pip install?")` gate → run_install streams pip output char-by-char behind a Spinner → on success re-probe the import; failure prints the exact manual command.

**Flow:** ensurepip best-effort (`check=False`, exceptions ignored) → Popen with merged stdout, `bufsize=1`, `errors="replace"` → spinner per char → exit-code verdict.
**Invariant:** consent is required before ANY network-mutating pip run; a successful install is verified by re-importing, not by trusting pip's exit code; path helpers degrade to `"."` rather than raising when the filesystem is hostile.
**Probe:** `tests/basic/test_utils.py::test_safe_abs_path_symlink_loop` (:6) pins the resolve-fallback helper; executed this run: `.pi/work/foundations-deep-farm/scratch-aider-pass2/probe_gate5.py::history-split-roles` (imports this module's splitter through the same wrapper chain). Install path itself: source-pinned only — no upstream direct test.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "aider", name_pattern: "IgnorantTemporaryDirectory", limit: 5 });
// also resolves: check_pip_install_extra, find_common_root, GitTemporaryDirectory
```

## Verdict
Adopt the swallow-list cleanup contract and the probe→consent→install→re-probe loop for any tool that self-installs extras; adapt the prompt copy and spinner; omit `format_tokens`/`touch_file` micro-helpers unless porting their call sites. Coverage caveat: only one direct upstream test in module; wrappers probe/source-pinned.

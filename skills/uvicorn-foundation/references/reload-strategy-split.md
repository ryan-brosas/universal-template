<!-- capsule-v2 -->
# Reload strategy split — how do watchfiles and stat fallback share one restart skeleton, and what is the .* special case?

**Source:** Uvicorn BSD-3-Clause `main@9ee5694516b01f1d3d6ff9ed38f117fc869ee6ae`; Codebase Memory `ext-uvicorn`. **Question:** What does BaseReload own vs. the strategies, why does restart() on Windows send Ctrl+C, and when do include/exclude patterns silently not apply?

## Template-method: should_restart() abstract; pause = delay-bounded wait
**Path/Symbol:** `uvicorn/supervisors/basereload.py` — run loop :50–60, `pause` :62–66, win32 restart :87–97, subprocess re-create :99; strategies `watchfilesreload.py:FileFilter :11–45 + should_restart :47–53`, `statreload.py:should_restart :28–44`; import-time selection `supervisors/__init__.py:10–17`.
**Signature:** `def should_restart(self) -> list[Path] | None` (abstract); `def pause(self) -> None: if self.should_exit.wait(self.config.reload_delay): raise StopIteration()`.
**Data Shape:** default includes `["*.py"]`; default excludes `[".*", ".py[cod]", ".sw.*", "~*"]`; include/exclude only effective with watchfiles installed.

### Decisive source
```python
# basereload.py :62-66 — the tick: sleep reload_delay OR exit via StopIteration
def pause(self) -> None:
    if self.should_exit.wait(self.config.reload_delay):
        raise StopIteration()
...
# :86-98 — Windows can't terminate mid-reload cleanly; use CTRL_C_EVENT + flush nudge
os.kill(self.process.pid, signal.CTRL_C_EVENT)
sys.stdout.write(" ")   # non-empty string so the event is processed
sys.stdout.flush()
```
```python
# watchfilesreload.py :16-18 — ".*" would match ONLY hidden dirs; keep it global-exclude
if pattern == ".*":
    continue  # pragma: py-not-linux
```

**Flow:** run(): startup (install handlers, spawn first child) → iterate `for changes in self:` where each `next()` = pause(reload_delay) then strategy's `should_restart()` → non-empty change list logs + restart(): terminate/CTRL_C the child, join, spawn a FRESH child with same target+sockets → loop ends on StopIteration → shutdown closes sockets. WatchFilesReload delegates change detection to `watchfiles.watch(stop_event=should_exit)` filtered through FileFilter (include-match minus exclude-dir/pattern); StatReload rglobs *.py per reload_dir comparing mtimes and RESETS its mtimes map on every restart.
**Invariant:** Only ONE child exists at a time; sockets are never rebound across restarts. The `.*` skip in resolve/FileFilter prevents the hidden-dir-only interpretation of the default exclude. StatReload warns that patterns are inert without watchfiles — a documented silent degradation.
**Probe:** from the uvicorn checkout root: `bash -c "grep -c 'should_exit.wait(self.config.reload_delay)' uvicorn/uvicorn/supervisors/basereload.py"` → 1; `bash -c "grep -cF 'sys.stdout.write(\" \")' uvicorn/uvicorn/supervisors/basereload.py"` → 1. Behavioral pins: `tests/supervisors/test_reload.py:test_reload_when_python_file_is_changed` :108, `test_should_not_reload_when_dot_file_is_changed` :189, `test_display_path_relative` :345.
**Retrieve:** `search_graph {"project":"ext-uvicorn","query":"reload strategy stat watchfiles should_restart","limit":5,"detail":"ids"}` → resolves BaseReload/strategy classes line-exact.
**Verdict:** Adopt template-method split verbatim. Adapt watcher backend to host. Omit win32 CTRL_C_EVENT dance if you have POSIX signals only.


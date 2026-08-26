<!-- capsule-v2 -->
# Brand-laundered CLI delegation facade — how do you rebrand a foreign package's CLI as your own without forking it?

**Source:** browser-use MIT `main@85ddbfedf609`; Codebase Memory `browser-use`. **Question:** how does a thin `cli.py` hand every real command to an external package (`browser_harness`) while users see only the local brand, telemetry stays attributed correctly, and old subcommands fail with useful migrations?

## Connected graph-selected seam
**Path/Symbol:** `browser_use/cli.py` (464L, whole read) — `_dispatch` (:357-400), `_run_browser_harness` (:185-202), `_patch_browser_harness_cli_text` (:159-179), `_normalize_captured_cli_output` (:134-156), `_raised_from_piped_code` (:294-300), `_StderrTail` (:403-415), `main` (:423-458).
**Signature:** `main() -> int | None` wraps `_dispatch(args) -> tuple[int | None, str]`; module global `_delegated_to_harness: bool`.
**Data Shape:** dispatch ladder on raw argv; legacy map `_LEGACY_HINTS: dict[str, str]` (command → migration hint); exit codes normalized as `None→0, int→passthrough, str→print+rc 1`.

### Decisive source
```python
# _dispatch ladder — order matters; harness run is the FALLTHROUGH
if '--cli-mcp' in args: ...        # 1. MCP stdio servers first
if '--mcp' in args: ...
install → init (+ --template/-t) → skill → legacy hints (rc 2)
if not args:
    if sys.stdin.isatty(): print(_QUICKSTART)          # TTY quickstart
    code = sys.stdin.read(); sys.stdin = StringIO(code) # piped Python re-injected
try:
    return _run_browser_harness(), args[0] if args else 'run'
except NameError as exc:           # unknown helper in PIPED code only
    if name is None or not _raised_from_piped_code(exc): raise

def _raised_from_piped_code(exc):  # walk to the LAST traceback frame
    while tb is not None: last = tb; tb = tb.tb_next
    return last.tb_frame.f_code.co_filename == '<string>'

def _run_browser_harness():
    _set_harness_client_env()          # BH_CLIENT=browser-use-cli + version
    _patch_browser_harness_cli_text()  # launder HELP/USAGE + auth/telemetry CLIs
    ...
    _delegated_to_harness = True       # suppresses browser-use-side telemetry
    run.main()

class _StderrTail:                     # pass-through stderr that keeps context
    def write(self, text):
        self.tail = (self.tail + text)[-500:]   # rolling 500-char tail
        return self._wrapped.write(text)
```
```python
def _as_browser_use_cli_text(text):    # brand laundering, captured output only
    return text.replace('Browser Harness', 'Browser Use').replace('browser-harness', 'browser-use')

# selective capture: auth CLI only when asking for help; telemetry CLI only for
# UNKNOWN subcommands (status/enable/disable pass through untouched)
if any(arg in {'-h', '--help'} for arg in argv): return _normalize_captured_cli_output(...)
if argv and argv != ['status'] and argv != ['enable'] and argv != ['disable']: ...
```
**Flow:** main stamps stderr with `_StderrTail`, records start time and command name → `_dispatch` runs the ladder → harness path monkeypatches the foreign package's HELP/USAGE strings and wraps its auth/telemetry CLIs with capture-and-launder before delegating → `main` catches SystemExit/Exception, reports telemetry ONLY if not delegated, restores stderr in finally → str exit codes reach `sys.exit(result)` whose str semantics print the message and exit 1.
**Invariant:** telemetry attribution follows OWNERSHIP, not failure — when the harness owns the run (`_delegated_to_harness`), browser-use-side `capture_cli_event` is suppressed entirely; laundering applies to CAPTURED output and patched constants only, never by intercepting arbitrary writes; NameError→friendly-helper-message rewriting fires exclusively for exceptions whose deepest traceback frame is `<string>` (exec'd stdin), so genuine bugs in package code still raise.
**Probe:** direct tests executed green this pass: `.venv/bin/python -m pytest -q tests/ci/test_browser_use_cli.py` → 3 passed (byte-exact `usage: browser-use doctor [--fix-snap]\n` stdout with empty stderr; `_normalize_captured_cli_output` turning `SystemExit('browser-harness failed')` into rc 1 + laundered stderr `'browser-use failed\n'`; tui deprecation alias).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-use", query: "_dispatch _run_browser_harness _StderrTail _raised_from_piped_code _normalize_captured_cli_output legacy hints", limit: 10, fields: ["lines"] });
```
Top hits: `_run_browser_harness` :185-202, `_raised_from_piped_code` :294-300, `_normalize_captured_cli_output` :134-156, `_dispatch` :357-400, `_legacy_migration_message` :254-269, plus the pinning test node.

## Verdict
Adopt the delegation-facade shape: fallthrough dispatch with the external runner last, module-global ownership flag gating YOUR telemetry, selective capture-and-launder of foreign help text, and a bounded stderr tail as error context. Adapt the brand-replacement pairs, the legacy-hint vocabulary, and BH_* env names. Omit the product quickstart copy. If you don't exec user code from stdin, the `<string>` frame check has no target — keep the ownership/laundering halves instead.

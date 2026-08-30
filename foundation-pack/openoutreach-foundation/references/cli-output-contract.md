<!-- capsule-v2 -->
# CLI output contract — how does a command line serve a human and a program at once: stdout result-only, typed one-line failures, no traceback for expected errors?

**Source:** OpenOutreach GPL-3.0 `main@c3ac1434118ac5301b193506d1d01e6e313bc622`; Codebase Memory `openoutreach`. **Question:** Where do logs, banners, colors, and errors go so that redirecting stdout yields data and nothing else — and which exceptions deserve to be flattened?

## Connected graph-selected seam
**Path/Symbol:** `openoutreach/core/management/base.py` — `OpenOutreachCommand.execute` (:37-41), `.run_from_argv` (:43-53), `format_failure` (:56-66), `require_initialized_database` (:69-94); `core/logging.py` — `_color_enabled` (:75-87), `SILENCED_LOGGERS` (:137-146), `_pin_termcolor_to_stderr` (:156-171), `configure_logging` (:174-191).
**Signature:** `format_failure(exc: OpenOutreachError, *, as_json: bool) -> str`; `require_initialized_database() -> None`.
**Data Shape:** failure line grammar `error: <type>: <message>` (types from the stable ErrorType vocabulary); JSON failure `{"error": {"type", "message"}}`.
**Graph evidence:** search_graph "OpenOutreachCommand stdout stderr json output command base" (46 total; class + format_failure + guard + `_pin_termcolor_to_stderr` all top hits); trace inbound `format_failure` = `run_from_argv` only.

### Decisive source
```python
        try:
            super().run_from_argv(argv)
        except OpenOutreachError as exc:
            sys.stderr.write(format_failure(exc, as_json="--json" in argv))
            sys.exit(1)
```
And the rule that surprises porters (:57-63):
```python
    """The failure as the caller asked to be spoken to — one line, or one object.

    **Both go to stderr.** A caller that passed ``--json`` is parsing, not reading, so
    an error it cannot parse is barely better than none; but stdout stays result-only
    either way, or ``find 10 --json > leads.json`` would write an error object into the
    file the operator is keeping."""
```

**Flow:** every verb subclasses `OpenOutreachCommand`; after argument parsing (so `--help` still answers) `execute` runs the schema guard → missing table or behind-on-migrations DB raises typed `NOT_INITIALIZED` ("answering with zero campaigns instead would be the empty-result failure the error vocabulary exists to prevent") instead of Django's raw `no such table` → expected failures render as one stderr line/JSON object and exit 1; anything else keeps Django's traceback because it is a bug. Logging plane backs the same promise: handler on stderr, banner on stderr, termcolor's cached stdout-TTY answer pinned to stderr before the first `colored()` call (unless NO_COLOR/FORCE_COLOR), noisy SDK loggers held at WARNING regardless of `--log-level`.
**Invariant:** stdout carries results only — even for JSON askers. Only `OpenOutreachError` flattens; unexpected exceptions propagate. The migrating verb opts out via class attr (`requires_database = False`) rather than a special case. Color gating keys on **stderr** TTY, so piping the result never strips interactive color.
**Probe:** `tests/test_output_contract.py` whole (198 L) — `test_logs_go_to_stderr_not_stdout` (:26-38), `test_command_renders_the_error_line_and_exits_non_zero` (:59-71), `test_json_callers_get_the_failure_as_json` (:74-95, asserts `captured.out == ""`), `test_an_unexpected_exception_still_raises` (:98-105), `test_reading_an_unmigrated_database_is_a_typed_error` (:110-123), `test_the_verb_that_migrates_is_not_guarded` (:126-137).
**Coverage:** `check_index_coverage` core/management/base.py, tests/test_output_contract.py, core/logging.py, openoutreach/__main__.py → no_recorded_issue / metadata_match @ gen 2026-08-25T20:08:16Z. (test_output_contract.py :140-198 bettercontact 429 ranges are owned by the existing bettercontact-async-split capsule.)

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "openoutreach", query: "OpenOutreachCommand run_from_argv format_failure", limit: 10 });
```

## Verdict
Adopt: base-class output contract (result-only stdout, stderr-everything-else, typed one-line/JSON expected failures with exit 1, traceback-preserving bugs, pre-work schema guard with an opt-out for the bootstrapping verb). Adapt the error vocabulary to yours; omit termcolor pinning if your color library gates correctly — but verify it caches per-stream before assuming so.

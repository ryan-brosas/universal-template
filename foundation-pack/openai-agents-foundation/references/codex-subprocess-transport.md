<!-- capsule-v2 -->
# Codex CLI subprocess transport — how do you drive a line-oriented JSONL subprocess with cancellation, idle timeouts, and oversized lines without truncation or leaked processes?

**Source:** OpenAI Agents Python MIT `main@fe45b415ee05`; Codebase Memory project `openai-agents-python` (MCP absent this pass — direct source+test reading fallback per AGENTS.md). **Question:** How does the Codex extension spawn, stream, cancel, and reap a CLI subprocess whose stdout is one JSON event per line, so that huge tool-output lines are not truncated, an idle stream is detected, cooperative cancellation terminates the child, and no process or stderr is ever lost?

## Subprocess transport + thread/event plane
**Path/Symbol:** `src/agents/extensions/experimental/codex/exec.py:` `CodexExec.run` (:61–212), `_read_stdout_line` (:166–188), `_build_env` (:214–231), `_watch_signal` (:234–238), `find_codex_path` (:264–279), `_resolve_subprocess_stream_limit_bytes` (:282–296), `_validate_subprocess_stream_limit_bytes` (:299–307), constants :17–22; `thread.py:` `Thread.run_streamed` (:90–94), `_run_streamed_internal` (:96–160), `Thread.run` (:162–188), `_normalize_input` (:191–207), `_parse_event` (:210–214); `events.py:` `coerce_thread_event` (:111–160), `_UnknownThreadEvent` (:73–77), `coerce_usage` (:99–108); `items.py:` `coerce_thread_item` (:171–243), `_UnknownThreadItem` (:111–116).
**Signature:** `async def run(self, args: CodexExecArgs) -> AsyncGenerator[str, None]`; `def coerce_thread_event(raw: ThreadEvent | Mapping[str, Any]) -> ThreadEvent`.
**Data Shape:** stdout is JSONL (`codex exec --experimental-json`); `CodexExecArgs` carries input/base_url/api_key/thread_id/images/model/sandbox/working_directory/output_schema_file/signal (`asyncio.Event`)/idle_timeout_seconds/web_search/approval_policy; stream limit default 8 MiB, clamped 64 KiB–64 MiB, env-overridable via `OPENAI_AGENTS_CODEX_SUBPROCESS_STREAM_LIMIT_BYTES`.

### Decisive source
```python
process = await asyncio.create_subprocess_exec(
    self._executable_path, *command_args,
    stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE,
    # Codex emits one JSON event per line; large tool outputs can exceed asyncio's
    # default 64 KiB readline limit.
    limit=self._subprocess_stream_limit_bytes,
    env=env,
)
...
async def _read_stdout_line() -> bytes:
    if args.idle_timeout_seconds is None:
        return await stdout.readline()
    read_task = asyncio.create_task(stdout.readline())
    done, _ = await asyncio.wait({read_task}, timeout=args.idle_timeout_seconds,
                                return_when=asyncio.FIRST_COMPLETED)
    if read_task in done:
        return read_task.result()
    if args.signal is not None:
        args.signal.set()
    if process.returncode is None:
        process.terminate()
    read_task.cancel()
    with contextlib.suppress(asyncio.CancelledError, asyncio.TimeoutError):
        await asyncio.wait_for(read_task, timeout=1)
    raise RuntimeError(f"Codex stream idle for {args.idle_timeout_seconds} seconds.")
```
and the coercion contract that never drops unknown events:
```python
def coerce_thread_event(raw):
    ...
    return _UnknownThreadEvent(type=..., payload=dict(raw))   # unknown type, kept as data
```

**Flow:** argv built as `exec --experimental-json` + per-option flags (`--config key="value"` for reasoning effort / network access / web search / approval policy); a thread_id appends `resume` EARLY and then `-- <thread_id>` late, so an option-looking thread id can never be parsed as a flag (pinned by `test_codex_exec_run_treats_option_like_thread_id_as_positional`); prompt goes to stdin (`-` argument) which is closed after drain; env = override mapping or filtered `os.environ`, plus `CODEX_INTERNAL_ORIGINATOR_OVERRIDE=codex_sdk_ts` default and per-call `OPENAI_BASE_URL`/`CODEX_API_KEY`; stderr is drained concurrently into a chunk list so a chatty child can never block stdout reads; each stdout line is read through the idle-timeout wrapper (no timeout ⇒ plain `readline`); on timeout the cooperative signal Event is set, the process terminated, the read task cancelled and reaped with a 1 s grace, and a `RuntimeError` raised; a separate `_watch_signal` task terminates the child whenever the caller sets the Event (AbortSignal mirror); after EOF the process is awaited, the watcher cancelled, and a non-zero exit raises `RuntimeError` carrying the drained stderr — AFTER the stream was fully consumed; the `finally` kills any still-running child. `Thread._run_streamed_internal` wraps the line generator in `_aclosing`, parses each line with `_parse_event` → `coerce_thread_event` (typed frozen dataclasses; unknown event/item types become `_UnknownThreadEvent`/`_UnknownThreadItem` payload passthrough instead of being dropped), captures `thread.started`'s id so callers can resume, and re-raises parse failures as `RuntimeError` including the raw item; `Thread.run` aggregates events into a `Turn` (last agent_message text wins, `TurnCompletedEvent` supplies usage, `TurnFailedEvent` breaks then raises, `ThreadErrorEvent` raises immediately); the structured-output temp file is created per streamed turn and removed in `finally` (cleanup swallows rmtree errors).

**Invariant:** (1) A completed request's stderr is never lost and never blocks stdout — it is drained concurrently and reported only on non-zero exit. (2) An oversized single-line event is delivered whole because the readline limit is raised at spawn, not by post-hoc joining. (3) Cancellation is cooperative AND hard: the Event watcher terminates the child, the idle timeout terminates it too, and the `finally` kills anything left — no leaked process on any exit path. (4) Unknown event/item types survive as typed passthrough objects; the parser never discards data it does not recognize.

**Probe:** `tests/extensions/experiemental/codex/test_codex_exec_thread.py` — `test_codex_exec_run_builds_command_args_and_env` (:280, exact argv + env contract), `test_codex_exec_run_treats_option_like_thread_id_as_positional` (:359), `test_codex_exec_run_handles_large_single_line_events` (:385, >64 KiB line delivered whole at the default limit), `test_codex_exec_run_web_search_enabled_flags` (:433), `test_codex_exec_run_raises_on_non_zero_exit` (:455, stderr surfaced), `test_codex_exec_run_raises_without_stdin` (:474) / `..._without_stdout` (:492), `test_watch_signal_terminates_process` (:510), `test_thread_run_streamed_idle_timeout_sets_signal` (:724) / `..._creates_signal` (:756), `test_thread_run_streamed_raises_on_parse_error` (:701), `test_output_schema_file_cleanup_swallows_rmtree_errors` (:134); `test_payloads.py` (coercion units).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openai-agents-python", query: "codex exec subprocess jsonl stream limit idle timeout signal terminate stderr drain", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the spawn-time readline-limit raise, the concurrent stderr drain, the idle-timeout ladder (set signal → terminate → cancel+reap read task → raise), and the never-drop unknown-event coercion — all four port directly to any JSONL-subprocess integration. Adapt the argv grammar (`--config key="value"`, `resume` + `--` separator) to your CLI's own contract. Omit the vendored-binary platform-triple lookup (`find_codex_path`) if your host installs the binary via PATH only. Coverage caveat: MCP absent this pass; Retrieve block is the canonical shape, not an executed call; all citations line-verified by grep against HEAD fe45b415ee05.

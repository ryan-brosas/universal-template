<!-- capsule-v2 -->
# codex_tool wrapper — how do you wrap a stateful external agent session as a function tool while keeping thread identity recoverable across failures and cancellations?

**Source:** OpenAI Agents Python MIT `main@fe45b415ee05`; Codebase Memory project `openai-agents-python` (MCP absent this pass — direct source+test reading fallback per AGENTS.md). **Question:** How does the SDK expose a whole Codex agent run as one function tool, resolve and persist the Codex thread id across calls, failures, and cancellations, and stream events to observers without letting user callbacks block the CLI stream?

## Agent-tool factory + run-context thread-id plane
**Path/Symbol:** `src/agents/extensions/experimental/codex/codex_tool.py:` `codex_tool` (:237–335), `_on_invoke_tool` (:337–429), `_resolve_codex_tool_name` (:470–488), `_resolve_run_context_thread_id_key` (:490–505), `_parse_tool_input` (:533–555), `_resolve_default_codex_api_key` (:607–629), `_create_codex_resolver` (:631–650), `_resolve_call_thread_id` (:834–852), `_validate_run_context_thread_id_context` (:875–924), `_store_thread_id_in_run_context` (:926–940), `_try_store_thread_id_in_run_context_after_error` (:957–974), `_get_or_create_persisted_thread` (:1006–1023), `_to_agent_usage` (:1025–1033), `_consume_events` (:1036–1140), `_handle_item_started` (:1142–1160), `_handle_item_completed` (:1186–1214), `_truncate_span_string` (:1216–1227); `src/agents/util/_asyncio_tasks.py:` `run_producer_consumer` (:117–157).
**Signature:** `def codex_tool(options: CodexToolOptions | Mapping[str, Any] | None = None, *, name=None, description=None, parameters=None, output_schema=None, codex=None, ..., use_run_context_thread_id: bool | None = None, run_context_thread_id_key: str | None = None) -> FunctionTool`; `async def _consume_events(events, args, ctx, thread, on_stream, span_data_max_chars, resolved_thread_id_holder=None) -> tuple[str, Usage | None, str | None]`.
**Data Shape:** returns a strict-schema `FunctionTool` (`_is_codex_tool = True` marker); invoke returns `CodexToolResult(thread_id, response, usage)`; run-context mode swaps the default parameters model to `CodexToolRunContextParameters` (thread_id hidden from the model); `resolved_thread_id_holder` dict carries the id out of `_consume_events` even when it raises.

### Decisive source
```python
except BaseException:
    resolved_thread_id = resolved_thread_id_holder["thread_id"]
    raise
...
except BaseException:
    _try_store_thread_id_in_run_context_after_error(
        ctx=ctx, key=resolved_run_context_thread_id_key,
        thread_id=resolved_thread_id,
        enabled=resolved_options.use_run_context_thread_id,
    )
    raise
```
and the non-blocking callback dispatch:
```python
if on_stream is not None:
    event_queue = asyncio.Queue()   # user callbacks cannot block the Codex stream loop
...
await run_producer_consumer(_process_events(), _dispatch())
```

**Flow:** factory overlays keyword args onto a coerced `CodexToolOptions` (`_UNSET` sentinel distinguishes "not passed" from `None` for `span_data_max_chars`/`failure_error_function`); name must be `"codex"` or `codex_`-prefixed; run-context mode derives a per-tool context key (`codex_thread_id_<suffix>`, suffix lossy-normalized, or strict `[A-Za-z0-9_]+`-validated when `use_run_context_thread_id=True`) and hides `thread_id` from the default tool schema; per call: parse input → resolve thread id by ladder (explicit tool input > run context > configured default) → get thread (persist_session=True reuses ONE closed-over `Thread`; a mismatched explicit id raises `UserError`) → always run `run_streamed` and aggregate; `_consume_events` walks events, dispatches `on_stream` payloads through a producer/consumer queue (`run_producer_consumer`: producer failure waits for consumer drain; consumer failure or parent cancellation cancels+drains the sibling), opens per-item custom spans for command-execution items (started/updated/completed keyed by item id; failed status sets a `SpanError`; every open span is force-finished in `finally`), truncates span values by `span_data_max_chars` with a `"... [truncated, N chars]"` suffix under a JSON-size budget, converts usage via `_to_agent_usage` (requests=1, total=input+output, cached tokens into `input_tokens_details`, reasoning_tokens=0) into `ctx.usage`, and raises `UserError` on `TurnFailedEvent`/`ThreadErrorEvent`; empty final response falls back to a deterministic default text; api-key ladder: options > env-override `CODEX_API_KEY` > `OPENAI_API_KEY` > `os.environ` same order > shared default OpenAI key; the `Codex` instance is created lazily exactly once via `_create_codex_resolver`.

**Invariant:** (1) The Codex thread id is written back to the run context on success AND on every failure path — recoverable turn failure, raised turn failure, cancellation, even handled parallel cancellation — so the next call resumes instead of restarting; a failure to store after an error is logged-and-swallowed so the original error propagates. (2) Context writability is validated BEFORE the call (mutable mapping ok; read-only mapping, frozen pydantic, frozen dataclass, undeclared `__slots__`, no-`__dict__` all rejected with targeted `UserError`s). (3) User stream callbacks can never block or break the CLI stream — they run on a drained queue and their exceptions are logged, not raised. (4) All spans opened for command items are closed even when the turn fails mid-stream.

**Probe:** `tests/extensions/experiemental/codex/test_codex_tool.py` — `test_codex_tool_persists_thread_id_for_recoverable_turn_failure` (:741) / `..._for_raised_turn_failure` (:778) / `..._for_cancelled_turn` (:818) / `..._for_handled_parallel_cancellation` (:869, the four recovery-path pins), `test_codex_tool_uses_run_context_thread_id_and_persists_latest` (:655), `test_codex_tool_run_context_thread_id_requires_mutable_context` (:1226) / `..._rejects_immutable_mapping_context` (:1263) / `..._rejects_frozen_pydantic_context` (:1300) / `..._rejects_frozen_dataclass_context` (:1341) / `..._rejects_slots_object_without_thread_field` (:1382), `test_codex_tool_streams_events_and_updates_usage` (:104), `test_codex_tool_persists_session` (:583), `test_codex_tool_persisted_thread_mismatch_raises` (:1618), `test_codex_tool_create_codex_resolver_caches_instance` (:1578), `test_codex_tool_truncates_span_values` (:501) / `..._enforces_span_data_budget` (:513), `test_codex_tool_default_run_context_key_follows_tool_name` (:1096), `test_codex_tool_resolve_codex_options_reads_env_override` (:1566).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase-memory.search_graph({ project: "openai-agents-python", query: "codex tool run context thread id persist producer consumer queue span truncation", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the thread-id recovery contract (store on success and on every `BaseException`, holder dict carries the id out of a raising consume loop) and the queue-mediated observer dispatch — both generalize to any agent-as-tool over a stateful backend. Adapt the context-writability validator to your own context vocabulary (the frozen-pydantic/`__slots__` ladder is Python-specific but the check-before-call ordering is not). Omit the api-key env ladder and vendored-binary resolution if your host injects credentials differently. Coverage caveat: MCP absent this pass; Retrieve block is the canonical shape, not an executed call; all citations line-verified by grep against HEAD fe45b415ee05.

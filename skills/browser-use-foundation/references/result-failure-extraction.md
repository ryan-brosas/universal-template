<!-- capsule-v2 -->
# Result/failure extraction ladder — how do you decide success, and which failure message wins, from an event log?

**Source:** browser-use MIT `main@3c989dc`; Codebase Memory `browser-use`. **Question:** given events plus an optional transport-level process error, what is the deterministic precedence that yields (final_result, failure, is_done)?

## Connected graph-selected seam
**Path/Symbol:** `browser_use/beta/service.py` — result ladder `_done_tool_result_from_events` (:1639) → `_result_from_events` (:1664) → `_last_streamed_assistant_text_from_events` (:1690); attachments `_attachments_from_events` (:1703); structured salvage `_json_result_candidates` (:1737) + `_structured_result_text` (:1761); failure ladder `_failure_from_events` (:1776), `_recoverable_failure_from_events` (:1810); orchestrator `_history_from_events` :3990-4022.
**Signature:** `_history_from_events(events, *, model, started, finished, output_model_schema, process_error) -> AgentHistoryList`.
**Data Shape:** terminal markers `session.done {result|result_file}`, `session.failed/stream_error {error|message}`, `session.cancelled/interrupted {reason}`, `agent.failed/agent.cancelled`; recoverable `tool.failed/tool.aborted/exec_command.end(non-zero)/model.turn.error/model.turn.context_overflow` + operational labels (`browser.cleanup_timed_out`, `session.compaction_failed`, …).

### Decisive source
```python
events = _events_after_terminal_rollbacks(_events_after_terminal_compaction(events))
final_result = _structured_result_text(_result_from_events(events), output_model_schema)
failure = process_error or _failure_from_events(events)
if final_result is None and failure is not None:
    final_result = _structured_result_text(_last_streamed_assistant_text_from_events(events), schema)  # graceful degrade
if final_result is None and failure is None:
    failure = _recoverable_failure_from_events(events)      # tool-level errors surface as failure ONLY if nothing succeeded
if final_result is None and failure is None:
    failure = 'Rust terminal session did not produce a final result.'
is_done = final_result is not None and failure is None
# transport error AFTER a final result is not a failure:
if events_result is not None and (process_error == 'CancelledError'
        or _sdk_transport_error_after_final_result(process_error)):   # :669 fragment list
    process_error = None
# structured-output salvage: validate every JSON candidate, return the FIRST that parses:
for candidate in _json_result_candidates(result):     # whole text → ```json fences → raw_decode at each '{'/'['
    output_model_schema.model_validate_json(candidate); return candidate
```

**Flow:** fold replays → try done-tool text (`name == 'done'`, keys `text|result|answer`, strips a leading `'done:'`) → session.done result or its `result_file` pointer ("Saved result file.") → agent.completed nested payload; on failure-with-partial-work, fall back to the last streamed assistant text; only when nothing succeeded do tool-level failures become THE failure (session.cancelled/interrupted get fixed "Rust terminal session was cancelled." phrasing with optional reason); attachments collected across `session.done/result_file`, `artifact.created`, `tool.output_spilled`, `capture.curation.gif_path`, `tool.output/failed.text_artifact+artifacts` (images excluded).
**Invariant:** precedence is strict — session-level beats tool-level; a final result neutralizes post-final transport errors (four exact stderr fragments) so a crash after completion still reports success; structured-output validation never invents data — if no candidate validates the RAW text is returned unchanged.
**Probe:** `tests/ci/test_beta_agent.py:2962` `test_beta_agent_recovers_final_result_from_sdk_notifications_after_transport_error`; `:7543` `test_rust_history_process_failure_ignores_empty_stream_text`; `:7581` `test_rust_history_surfaces_terminal_stream_error_message`; `:7889` `test_rust_history_surfaces_terminal_session_interrupted_message`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-use", query: "_result_from_events _failure_from_events _sdk_transport_error_after_final_result", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the full precedence chain (done-tool → session marker → streamed fallback; transport-error forgiveness after final result) for any remote-agent bridge; adapt marker names/phrasings; omit the browser-use cloud artifact kinds you don't emit.

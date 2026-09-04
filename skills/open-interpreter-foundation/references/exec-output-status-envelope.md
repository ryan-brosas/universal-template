<!-- capsule-v2 -->
# exec-output-status-envelope — how is a yielded vs completed vs failed cell result framed for the model?

**Source:** open-interpreter Apache-2.0 `main@5b07159c477920c159d8892d112b480e7307f257`; Codebase Memory `ext-open-interpreter`. **Question:** What exact text/status does the model receive for each RuntimeResponse variant, and what gets truncated?

## handle_runtime_response framing
**Path/Symbol:** `codex-rs/core/src/tools/code_mode/mod.rs` : `handle_runtime_response` (:233-277), `format_script_status` (:283-297), `prepend_script_status` (:299-307), `truncate_code_mode_result` (:309-325).
**Data Shape:** every output = [status header text item] + content items (+ trailing `Script error:\n{error}` item on failure); header = `"{status}\nWall time {s:.1} seconds\nOutput:\n"` with wall time rounded to 0.1s.

### Decisive source
```rust
RuntimeResponse::Result { content_items, error_text, .. } => {
    ...
    let success = error_text.is_none();
    if let Some(error_text) = error_text {
        content_items.push(FunctionCallOutputContentItem::InputText {
            text: format!("Script error:\n{error_text}"),
        });
    }
    content_items = truncate_code_mode_result(content_items, max_output_tokens);
    prepend_script_status(&mut content_items, &script_status, started_at.elapsed());
    Ok(FunctionToolOutput::from_content(content_items, Some(success)))
}
```

**Flow:** Yielded/Terminated → success=true with status "Script running with cell ID {id}" / "Script terminated"; Result → "Script completed"/"Script failed". Truncation: all-text outputs use the formatted head+tail truncator; mixed outputs use per-item policy with audio token estimation; over-budget audio items collapse to `"[omitted N audio items ...]"`.
**Invariant:** The status header is PREPENDED AFTER truncation so the model always sees the full banner even when output is clipped. Yielded cells return `success=true` — a pending script is not an error. Image detail is sanitized against model capability (`can_request_original_image_detail`) BEFORE truncation.
**Probe:** mod.rs tests at pin: `truncated_text_output_starts_with_warning` (exact warning string + 10-token count), `over_budget_audio_output_is_omitted`.

## wait tool surface
**Path/Symbol:** `core/src/tools/code_mode/wait_handler.rs` : `ExecWaitArgs` (:24-33), hook bypass (:170-188).
**Data Shape:** JSON args `{cell_id (required), yield_time_ms=10000, max_tokens?, terminate=false}`; terminate:true routes to session.terminate instead of wait.
**Invariant:** wait/exec are exempt from PreToolUse/PostToolUse hooks (`None` payloads) — hooks must never block or rewrite runtime-control calls; nested REAL tool calls still flow through normal dispatch and CAN be hooked.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-open-interpreter", query: "handle_runtime_response format_script_status truncate_code_mode_result", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the status-header envelope, post-truncation prepend ordering, and hook exemption for control tools. Adapt wording/wall-time formatting. Omit analytics guard telemetry.

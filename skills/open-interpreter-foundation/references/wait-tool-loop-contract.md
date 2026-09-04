<!-- capsule-v2 -->
# wait-tool-loop-contract — what makes the exec/wait pair a complete code-action loop for low-cost models?

**Source:** open-interpreter Apache-2.0 `main@5b07159c477920c159d8892d112b480e7307f257`; Codebase Memory `ext-open-interpreter`. **Question:** How do the two public tools cooperate so a model can run long scripts without long tool-call timeouts?

## Two-tool split
**Path/Symbol:** `codex-rs/core/src/tools/code_mode/execute_spec.rs` : `create_code_mode_tool` (:15-45); `wait_spec.rs` : `create_wait_tool` (:11-46); `wait_handler.rs` : `handle_call` (:63-168).
**Data Shape:** `exec` = Freeform tool (raw JS source, lark grammar allowing optional first-line pragma) → returns yield/completion envelope; `wait` = strict=false Function tool `{cell_id, yield_time_ms=10000, max_tokens?, terminate=false}` → routes to session.wait or session.terminate.

### Decisive source
```rust
// execute_spec.rs — constrained grammar mirrors parse_exec_source
start: pragma_source | plain_source
pragma_source: PRAGMA_LINE NEWLINE SOURCE
plain_source: SOURCE
PRAGMA_LINE: /[ \t]*\\/\\/ @exec:[^\\r\\n]*/
NEWLINE: /\\r?\\n/
SOURCE: /[\\s\\S]+/
```

**Flow:** model emits exec → handler parses pragma → enabled-tool definitions gathered (cached per runtime when available, else rebuilt; schemas STRIPPED before sending to the cell: `definition.input_schema = None`) → sorted+deduped by name → session.execute → first response framed with "Script running with cell ID {id}" → model polls wait → each wait returns ONLY new items since last yield → terminate:true force-stops.
**Flow (lifecycle):** terminal responses (non-Yielded) close the dispatch gate, record trace end, emit CellClosed analytics — in BOTH the execute handler and the wait handler, because a cell can reach its end during any observe call.
**Invariant:** The enabled-tools snapshot travels WITH the execute request (the cell's `tools` object is built from it at spawn) — tools registered later in the turn are invisible to already-started cells. Schema stripping keeps the V8-side metadata small; the TS declarations live only in the PROMPT. wait is hook-exempt but nested calls it triggers are not.
**Probe:** execute_spec/wait_spec in-file tests pin exact ToolSpec JSON at the pinned commit.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-open-interpreter", query: "create_code_mode_tool create_wait_tool CODE_MODE_FREEFORM_GRAMMAR", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the freeform-exec + function-wait pairing with request-carried tool snapshots and schema stripping. Adapt grammar syntax to your constrained-decoding support. Omit analytics facts.

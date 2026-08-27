---
name: openai-swarm-foundation
description: "Use when porting or building a minimal agent runtime (tool-call loop, agent handoffs, shared context), designing a triage/router multi-agent topology, generating OpenAI tools schemas from Python functions, reassembling streamed chat-completion deltas, or testing agent loops without a live model. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval."
---
# openai-swarm: minimal-agent foundation

## Use this for
Use when porting or building a minimal agent runtime (tool-call loop, agent handoffs, shared context), designing a triage/router multi-agent topology, generating OpenAI tools schemas from Python functions, reassembling streamed chat-completion deltas, or testing agent loops without a live model. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `references/runloop-turn-machine.md` — what one turn covers, stop conditions, copy-vs-mutate discipline (`max_turns` counts appended messages).
- `references/handoff-protocol.md` — Agent-returning functions switch the active agent while the model only ever sees `{"assistant": "<name>"}` text.
- `references/context-variables-plumbing.md` — name-keyed injection of a shared dict into tools/instructions with schema stripping so it never reaches the wire.
- `references/toolcall-execution-errors.md` — per-call isolation; unknown-tool errors are tool messages, but arg-parse/exec exceptions kill the run.
- `references/function-to-json-schema.md` — 40-line signature→tools-schema converter; untyped params silently become strings.
- `references/streaming-merge-chunk.md` — index-keyed recursive string-append accumulator that rebuilds parallel tool_calls from SSE shards.
- `references/run-and-stream-consumer.md` — generator contract (delims, sender-enriched deltas, terminal response envelope) over the same loop.
- `references/types-agent-response-result.md` — the complete ontology: 6-field Agent, Response, Result; stateless reentrant agents.
- `references/request-assembly.md` — per-turn system-prompt regeneration + verbatim param forwarding (`parallel_tool_calls` only when tools exist).
- `references/history-dict-boundary.md` — one serialization boundary (`model_dump_json` round-trip) keeps history uniformly dicts and preserves `sender`.
- `references/mock-client-harness.md` — one-method duck-typed fake client + scripted ChatCompletions = deterministic multi-turn loop tests.
- `references/repl-streaming-consumer.md` — reference chunk consumer (latch sender, reset on delim-end) and extend-don't-replace history accumulation.
- `references/triage-router-pattern.md` — canonical router/specialist wiring: zero-arg transfer closures plus explicit back-transfers.

## Capsule map
- **Run loop** — `runloop-turn-machine`: deepcopy inputs; turn = completion + optional tool batch; `Response.messages` is new-only.
- **Handoffs** — `handoff-protocol`: return an Agent from a tool → control flow swaps, transcript gets JSON name trace.
- **Shared memory** — `context-variables-plumbing`: `context_variables` param name opts in; schema surgery hides it from the model.
- **Tool execution** — `toolcall-execution-errors`: missing tool → error tool message + continue; no try/except around parse/execute.
- **Schema generation** — `function-to-json-schema`: inspect-based envelope; string fallback for unannotated types; defaults drive required.
- **Stream assembly** — `streaming-merge-chunk`: merge_fields concatenation + tool_call index keying; role stripped pre-merge.
- **Streaming surface** — `run-and-stream-consumer`: same loop as generator; consumers get delims/deltas/response vocabulary.
- **Data model** — `types-agent-response-result`: Agent(name/model/instructions/functions/tool_choice/parallel_tool_calls); Result(value/agent/context).
- **Request compiler** — `request-assembly`: fresh system message each turn; model_override precedence; tools-or-None.
- **History boundary** — `history-dict-boundary`: pydantic→dict at ingress keeps `sender` and uniform subscript access.
- **Test rig** — `mock-client-harness`: side_effect-scripted real ChatCompletion objects through a duck-typed client.
- **UI consumption** — `repl-streaming-consumer`: sender latching, delim resets, extend-master-history demo loop.
- **Topology pattern** — `triage-router-pattern`: instructions-only router, zero-arg transfers, back-transfer on specialists.

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
OpenAI Swarm (MIT), `main@6af0b4caf37dca4526dfd98e9fbd8ce36e7eeb22`; Codebase Memory project `ext-openai-swarm` (full mode, head==base at pin, 1,783 nodes / 3,456 edges; all cited paths `no_recorded_issue`+`metadata_match`; only setup.cfg flagged parse-partial — packaging file, uncited).

## Full view (memory graph)
Revalidate `ext-openai-swarm` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Production plane is ~600 LOC across `swarm/core.py` (Swarm class: run / run_and_stream / handle_tool_calls / handle_function_result / get_chat_completion), `swarm/types.py`, `swarm/util.py`, `swarm/repl/repl.py`; direct tests in `tests/test_core.py` (4 tests) + `tests/test_util.py` (2 tests) via `tests/mock_client.py`. `examples/customer_service_streaming/src/swarm/` is a FORK of the engine inside examples (not indexed as separate package semantics; treat as variant reading, not canonical). Graph retrieval works well for Function/Method nodes; use text queries naming symbols.

## Boundaries
Adopt the pure contracts: turn machine, handoff routing, context plumbing, delta reassembly, schema conversion, scripted-test harness. Adapt the client seam to any chat-completions-shaped provider and the serializer to your stack. Omit OpenAI-specific wire assumptions if targeting other APIs, and do not treat `examples/**` engines (streaming fork) as canonical source — cite `swarm/` only.

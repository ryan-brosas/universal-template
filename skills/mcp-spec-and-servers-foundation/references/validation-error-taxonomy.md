<!-- capsule-v2 -->
# Tool error taxonomy (SEP-1303, Final) — which failures ride `isError: true` inside the result vs a `-32602` protocol error, and why it decides whether the LLM can self-correct

**Source:** modelcontextprotocol/specification MIT `main@4df2d6b6` (`seps/1303-input-validation-errors-as-tool-execution-errors.md`; normative text in `docs/specification/2026-07-28/server/tools.mdx` §Error Handling :738–786). Codebase Memory `modelcontextprotocol`. **Question:** When a `tools/call` fails on bad input, should the server return a JSON-RPC error or a result flagged `isError: true` — and what is the invariant a porter must not break?

## Input validation errors are TOOL EXECUTION errors (LLM-visible), not protocol errors
**Path/Symbol:** `seps/1303-input-validation-errors-as-tool-execution-errors.md` (whole SEP: motivation :9–52, spec change :54–90, before/after wire examples :92–161, backwards-compat :163–172); `docs/specification/2026-07-28/server/tools.mdx` §Error Handling :738–786 (normative two-mechanism split).

**Signature:** n/a — error-routing rule, not an API.

**Data Shape:** two disjoint mechanisms:
- **Protocol Errors** = JSON-RPC `error` object. Reserved for request-structure problems the model is unlikely to fix: unknown tool, malformed request (fails `CallToolRequest` schema), server errors. Example: `{ "code": -32602, "message": "Unknown tool: invalid_tool_name" }`.
- **Tool Execution Errors** = a `result` with `isError: true` + explanatory `content[]`. Reserved for actionable feedback the model can self-correct from: **input validation errors** (e.g. "date in wrong format, value out of range"), API failures, business-logic errors. Example: `{ "resultType": "complete", "content": [{ "type": "text", "text": "Invalid departure date: must be in the future. Current date is 08/08/2025." }], "isError": true }`.

### Decisive source
```md
# seps/1303 ...md — Specification (the clarifying change, verbatim)
1. Removes the "invalid argument" category from Protocol Errors.
2. Tool Execution Errors should be used for ALL tool argument validation failures
   (merging `invalid argument` and `invalid input data` under a new
   `input validation errors` category).
```
```md
# 2026-07-28/server/tools.mdx :738-786 (normative)
Tools use two error reporting mechanisms:
1. Protocol Errors ... Unknown tool; Malformed requests (fail CallToolRequest schema); Server errors.
2. Tool Execution Errors ... API failures; Input validation errors (e.g., date in wrong
   format, value out of range); Business logic errors. Reported in tool results with `isError: true`.
Clients MAY provide protocol errors to language models (less likely to recover).
Clients SHOULD provide tool execution errors to language models to enable self-correction.
```

**Flow:** tool receives arguments → schema-valid but semantically-invalid input (e.g. a past date that passes the regex) → server returns a **successful** JSON-RPC response whose `result.isError === true` and whose `content[0].text` explains WHY the input was rejected → the model sees the message in its context window and retries with corrected parameters → task completes without human intervention. If instead the server raises `-32602 Invalid params`, the client catches it at the application layer and the model never sees the reason — it retries blindly (the SEP documents Cursor repeating the same past date 3×).

**Invariant:** **the model can only self-correct from feedback that reaches its context window.** Protocol errors are swallowed by the client; only `isError: true` results are forwarded to the model. Therefore every *input validation* failure MUST ride `isError: true` (a Tool Execution Error), and only request-structure failures (unknown tool, malformed envelope, server fault) may be `-32xxx` protocol errors. A porter who raises protocol errors for tool-internal validation failures blinds the LLM and turns a recoverable mistake into a hard failure. This is the exact clarification SEP-1303 Final made to the previously ambiguous "invalid arguments vs invalid input data" guidance.

**Probe:** no runtime test in the spec repo (docs+SEP only — coverage caveat). Deterministic: the wire contrast is machine-checkable in `docs/specification/2026-07-28/server/tools.mdx` :738–786 (both example blocks above), and the reference servers follow it — e.g. `src/memory` returns validation outcomes as tool results, never as `-32xxx` errors.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "modelcontextprotocol", query: "isError Tool Execution Error input validation tools/call", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-mechanism split with input-validation failures ALWAYS as `isError: true` Tool Execution Errors (so the LLM can self-correct) and only request-structure failures as `-32xxx` protocol errors; adapt the error-message copy and validation depth to your tool catalog; omit treating "invalid argument" as a protocol error — that ambiguity is the exact bug SEP-1303 removed. Complements `schema-registration.md`/`content-blocks.md`, which pin the isError wire shape but not the validation-vs-execution routing taxonomy.

<!-- capsule-v2 -->
# Fake-MCP fixture plane — how do you test an MCP bridge end-to-end without a real IDE, with proof in BOTH directions?

**Source:** pi-acp-jetbrain MIT `main@1f0524f777c93c51747c26d24f3609c2a4e6731d`; Codebase Memory `pi-acp`. **Question:** How does a repo give its smoke tests deterministic stand-in MCP servers whose traffic is observable from OUTSIDE the adapter, so a test can assert both "the adapter discovered/registered the tool" and "the server actually received the call"?

## One NDJSON kernel + an append-only observation channel
**Path/Symbol:** `scripts/fixtures/fake-mcp-stdio.mjs` — `startFakeMcpServer({ serverName, timeoutMs, tools, handleToolCall })` (whole file, 71L); `scripts/fixtures/fake-mcp-server.mjs` (20L, echo tool for F-006/F-021/F-028); `scripts/fixtures/fake-mcp-inspect.mjs` (73L, lint_files/get_file_problems/run_inspection_kts for F-021/F-030); consumers `scripts/smoke-mcp-fixture.mjs` (115L) and `scripts/smoke-ide-inspect.mjs` (164L). Harness kernel in `references/acp-smoke-harness.md`.
**Signature:** `startFakeMcpServer({ serverName: string, timeoutMs: number, tools: Array<{name, description, inputSchema}>, handleToolCall(name: string, args: object): object })` — no return; runs until stdin ends/closes or `timeoutMs` elapses (hard exit 0).
**Data Shape:** speaks ONLY the JSON-RPC subset the bridge needs: `initialize` → `{protocolVersion:'2025-03-26', capabilities:{tools:{listChanged:false}}, serverInfo}`; `notifications/initialized` → ack-silence; `tools/list` → `{tools}`; `tools/call` → `handleToolCall(...)` result; anything else → `-32601 method not found`. Observation channel: env `FAKE_MCP_LOG` points at a JSONL file receiving `{type:'received', method, id}` per inbound message and `{type:'call', name, args}` per tool call.

### Decisive source
```js
// The observation channel is append-only JSONL written by the SERVER itself —
// the smoke script polls it with a deadline instead of trusting adapter output.
const logPath = process.env.FAKE_MCP_LOG ?? ''
const log = message => {
  if (!logPath) return
  try { appendFileSync(logPath, JSON.stringify(message) + '\n') } catch { /* ignore */ }
}
// ...
if (message.method === 'tools/call') {
  const args = message.params?.arguments ?? {}
  log({ type: 'call', name: message.params?.name, args })
  send({ jsonrpc: '2.0', id: message.id, result: handleToolCall(message.params?.name, args) })
  return
}
send({ jsonrpc: '2.0', id: message.id, error: { code: -32601, message: `method not found: ${message.method}` } })
```

**Flow:** smoke script mkdtemps a work dir, writes `FAKE_MCP_LOG=<work>/server.log`, declares the fixture as a stdio MCP descriptor (`command: process.execPath, args: [fixturePath]`) in `session/new.mcpServers`, then polls the log with a deadline-bounded `waitForLog(predicate, label, timeoutMs)` (100ms tick) for the discovery line (`received tools/list`) before asserting on adapter-side state (startupInfo "N tool registered"), and after a real model turn polls again for the call line (`call echo` / `call lint_files` with the expected args). fake-mcp-inspect returns DETERMINISTIC payloads: one fixed WARNING per linted file, and a run_inspection_kts result wrapped in a content-text JSON envelope so the adapter's unwrap ladder is exercised end-to-end. smoke-mcp-fixture additionally pins F-028: the descriptor's secret env value must never appear in adapter stderr, and the `PI_ACP_DEBUG_BRIDGE=1` dump must show `[redacted `.
**Invariant:** the fixture answers only the four bridge methods (unknown methods get -32601, never a hang), exits deterministically on stdin close OR hard timeout so a wedged adapter cannot leak the child, and every assertion about "the server saw X" reads the server's OWN log — bidirectional proof that neither side can fake the other. Tool results are fixed per input shape so report counts are assertable exactly.
**Probe:** `node scripts/smoke-mcp-fixture.mjs` (requires built dist + installed pi; asserts discovery, registration in startupInfo, real model-turn tool invocation via the log, and secret redaction) and `node scripts/smoke-ide-inspect.mjs` (asserts lint_files + run_inspection_kts invocations over a temp git repo's changed file, persisted report, `_meta.piAcp.inspection.status==='inspected'`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-acp", query: "startFakeMcpServer FAKE_MCP_LOG fake-mcp", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the single-kernel multi-fixture pattern (one NDJSON server factory, per-test tool tables + handlers), the server-side append-only JSONL observation channel polled with deadlines, the four-method-only surface with -32601 fallback, and the dual-exit (stdin-close OR timeout) liveness contract. Adapt the protocolVersion constant and the log-file env name to your transport. Omit the model-turn-dependent assertions if your host has no API credentials — the discovery/registration half still works without a turn. Smoke probes require built dist + installed pi (present this host: dist 3d5ffcd2e2d8, pi 0.84.x); see verification.md for execution status.

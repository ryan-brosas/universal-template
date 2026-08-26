<!-- capsule-v2 -->
# Bash terminal rendering — map pi bash tool events to ACP execute terminal output

**Source:** pi-acp-jetbrain MIT `main@27aac05f`; Codebase Memory `pi-acp`. **Question:** How does the adapter render pi's `bash` tool as an ACP `execute` terminal (delta output, exit metadata) instead of plain text?

## Bash terminal rendering
**Path/Symbol:** `src/acp/translate/bash.ts` (whole, 100L) + `src/acp/session.ts` `emitBashToolCall`/`emitBashOutputUpdate` (509-553).
**Signature:** `isBashTool(toolName): boolean`; `bashCommand(value): string|undefined`; `bashResultText(result): string`; `bashExitCode(result, isError): number`; `bashOutputDelta(prev, next): string`; `bashTerminalContent(toolCallId): ToolCallContent[]`; `bashTerminalInfoMeta/OutputMeta/ExitMeta`.
**Data Shape:** Bash args are matched across many shapes (`command`/`cmd` at top level or nested under `args`/`input`/`rawInput`/`toolInput`/`details`). Results carry `content` text blocks and/or `details.stdout`/`stderr`/`output`/`exitCode`/`code`.

### Decisive source
```ts
export function bashOutputDelta(previous: string, next: string): string {
  return next.startsWith(previous) ? next.slice(previous.length) : next
}
export function bashTerminalContent(toolCallId: string): ToolCallContent[] {
  return [{ type: 'terminal', terminalId: toolCallId }]
}
export function bashTerminalInfoMeta(toolCallId: string, cwd: string) {
  return { terminal_info: { terminal_id: toolCallId, cwd } }   // Zed renders execute as display-only terminals
}
export function bashTerminalOutputMeta(toolCallId: string, data: string) {
  return { terminal_output: { terminal_id: toolCallId, data } }
}
export function bashTerminalExitMeta(toolCallId: string, exitCode: number) {
  return { terminal_exit: { terminal_id: toolCallId, exit_code: exitCode, signal: null } }
}
```
```ts
// session.ts: emit only the delta since the last snapshot
const previous = this.bashOutputSnapshots.get(toolCallId) ?? ''
const delta = bashOutputDelta(previous, text)
this.bashOutputSnapshots.set(toolCallId, text)
this.emit({ sessionUpdate:'tool_call_update', toolCallId, status, _meta: {
  ...(delta ? bashTerminalOutputMeta(toolCallId, delta) : {}),
  ...(status==='completed'||status==='failed' ? bashTerminalExitMeta(toolCallId, bashExitCode(result, isError)) : {})
}})
```

**Flow:** On `toolcall_*`/`tool_execution_start` for a bash tool, emit a `tool_call` (or update) with `kind:'execute'`, `content: bashTerminalContent(id)` and `_meta: bashTerminalInfoMeta(id, cwd)` — this makes ACP clients render a display-only terminal. On `tool_execution_update`, emit only the output delta since the last snapshot. On `tool_execution_end`, emit the final delta + exit metadata (`completed`/`failed`).

**Invariant:** Bash output is streamed as deltas (prefix-diff against the previous snapshot), never re-sent in full; the terminal is identified by `toolCallId` across all three meta shapes; exit code defaults to `1` on error, `0` otherwise when absent.

**Probe:** `test/component/session-events.test.ts` ("PiAcpSession: emits tool_call + tool_call_update + completes" exercises the bash terminal path).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-acp", query: "bashOutputDelta bashTerminalExitMeta bashCommand", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the `kind:'execute'` + terminal-content + terminal-metadata rendering and the prefix-delta output streaming. Adapt the arg/result shape matchers and the ACP terminal meta keys to the target client. Omit the `bashResultText` multi-shape fallbacks unless the target agent's bash tool returns that variety.

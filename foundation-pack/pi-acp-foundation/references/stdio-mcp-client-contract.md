<!-- capsule-v2 -->
# Stdio MCP client contract — how do you wrap a spawned stdio MCP server so every failure carries its protocol phase and a sanitized stderr tail, and shut down without leaking pending requests?

**Source:** pi-acp-jetbrain MIT `main@1f0524f777c93c51747c26d24f3609c2a4e6731d`; Codebase Memory `pi-acp`. **Question:** How should a bridge wrap a spawned stdio MCP server so every failure carries its protocol phase and a sanitized stderr tail, and how does the client shut down without leaking pending requests?

## Stdio MCP client contract
**Path/Symbol:** `src/acp/mcp-stdio.ts` whole file (290L): `StdioMcpPhase` :10-17, `StdioMcpError` :18-38, `launchSummary` :40-42, `sanitizeStderr` :51-58, `exitError` :60-74, `StdioMcpClient` :76-290 (`#request` :192-233, `#waitForSpawn` :235-248, `#handleLine` :255-281, `#failPending` :283-288, `close` :167-190).
**Signature:** `static async start(server: McpServerStdio, cwd?, onNotification?): Promise<StdioMcpClient>`; `request(method, params, timeoutMs, requestId?, onRequestId?): Promise<unknown>`; `cancel(requestId): void`; `close(): Promise<void>`.
**Data Shape:** `StdioMcpPhase = 'spawn'|'initialize'|'initialized_notification'|'tools_list'|'runtime_call'|'close'`; `StdioMcpError` carries `{phase, launchSummary, exitCode?, signal?, sanitizedStderr?}`. Bounds: `MAX_STDERR_TAIL = 2_048` (rolling tail), `MAX_STDERR_DIAGNOSTIC = 512` (per-error excerpt).

### Decisive source
```ts
// sanitizeStderr: credential-shaped redaction BEFORE whitespace collapse, tail-sliced last
function sanitizeStderr(value: string): string {
  return value
    .replace(/Bearer\s+\S+/gi, 'Bearer [redacted]')
    .replace(/((?:authorization|token|secret|password)[=:]\s*)\S+/gi, '$1[redacted]')
    .replace(/\s+/g, ' ').trim().slice(-MAX_STDERR_DIAGNOSTIC)
}
// exitError: a dead child becomes a phase-tagged error with exit status + sanitized stderr
const status = code === null ? `signal=${signal ?? 'unknown'}` : `code=${code}`
return new StdioMcpError('spawn', `MCP stdio server exited (${status}; ${summary}${detail ? `; stderr: ${detail}` : ''})`, {...})
// close: SIGTERM, race the exit promise against 1s, then SIGKILL
await Promise.race([this.#exit, new Promise(resolve => setTimeout(resolve, 1000))])
if (this.#child.exitCode === null) this.#child.kill('SIGKILL')
```

**Flow:** `start` spawns with `shell:true` ONLY on win32 for `.cmd`/`.bat` commands, merges `server.env` over `process.env`, and awaits `#waitForSpawn` (spawn/error race; on failure closes the client and rethrows as a phase-`spawn` `StdioMcpError` with `launchSummary`). `#request` allocates the caller's id or the next internal one, arms a timeout that sends `notifications/cancelled` BEFORE rejecting, and registers `{resolve, reject, timer}` in `#pending`; a write failure rejects and cleans the entry synchronously. `#handleLine` routes: notification (method, no id) → `onNotification`; server-originated REQUEST (method + id) → `onNotification` with id AND an immediate `-32601` error echo (the server's request is never left hanging); response → `settlePendingJsonRpcResponse` (shared kernel). Child `close`/`error`/stdin-error all funnel into `#failPending(exitError(...))` so every pending caller is settled exactly once with the phase-tagged cause. `cancel` sends `notifications/cancelled` then rejects the local pending entry. `close` is idempotent (`#closePromise` memoized), fails pending first, SIGTERM → 1s race → SIGKILL.
**Invariant:** no pending request ever outlives its client: child exit, spawn failure, stdin error, explicit close, and timeout each settle the map exactly once; stderr is redacted before it can reach an error message; the launch summary (`command=<basename>; args=<n>; env=<n>; cwd=<path>`) identifies the server without leaking argv values.
**Probe:** NO direct unit test exists for `StdioMcpClient` at this pin (grep over `test/` = 0 hits; `test/unit/mcp-sse.test.ts` covers only the SSE twin). The settlement kernel it calls is pinned by `test/unit/mcp-json-rpc.test.ts` (executed GREEN pass 7). Recorded as a coverage caveat: this capsule is source-read only.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-acp", query: "StdioMcpClient StdioMcpError sanitizeStderr failPending", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the phase-tagged error taxonomy (spawn/initialize/tools_list/runtime_call), redact-then-truncate stderr handling, the launch-summary identifier, timeout-sends-cancel-before-reject, and the SIGTERM→timed-race→SIGKILL close ladder. Adapt phase names and env-merge policy to your host. Omit the win32 `.cmd` shell special-case if you do not target Windows. Coverage caveat: no direct unit test at this pin — port with one.

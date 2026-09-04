<!-- capsule-v2 -->
# ACP stdio server — how to wire the ACP server over stdio and tear it down

**Source:** pi-acp-jetbrain MIT `main@27aac05f`; Codebase Memory `pi-acp`. **Question:** How does the adapter speak ACP JSON-RPC 2.0 over stdio, handle the terminal-login entrypoint, and shut down cleanly when the client disconnects?

## ACP stdio server
**Path/Symbol:** `src/index.ts` (whole file, 82L).
**Signature:** `const stream = ndJsonStream(input, output); new AgentSideConnection(conn => new PiAcpAgent(conn), stream)`.
**Data Shape:** `input` = a `WritableStream<Uint8Array>` that writes to `process.stdout` (tolerating a destroyed/non-writable stdout — resolves without writing); `output` = a `ReadableStream<Uint8Array>` fed by `process.stdin` 'data'/'end'/'error'. The ACP SDK's `ndJsonStream` frames NDJSON in both directions.

### Decisive source
```ts
if (process.argv.includes('--terminal-login')) {
  const res = spawnSync(cmd, [], { stdio: 'inherit', env: process.env, shell: shouldUseShellForPiCommand(cmd) })
  process.exit(typeof res.status === 'number' ? res.status : 1)
}
const input = new WritableStream<Uint8Array>({
  write(chunk) {
    return new Promise<void>(resolve => {
      if ((process.stdout as any).destroyed || !process.stdout.writable) return resolve()
      try { process.stdout.write(chunk, err => { void err; resolve() }) } catch { resolve() }
    })
  }
})
// ... ndJsonStream(input, output) -> AgentSideConnection
process.stdin.on('end', shutdown); process.stdin.on('close', shutdown)
process.on('SIGINT', shutdown); process.on('SIGTERM', shutdown)
process.stdout.on('error', () => { try { process.exit(0) } catch {} })
function shutdown() { (agent as any)?.agent?.dispose?.(); try { process.exit(0) } catch {} }
```

**Flow:** `--terminal-login` re-launches the pi binary with inherited stdio and exits with pi's status → otherwise build the write-tolerant stdout stream + stdin-fed readable stream → `ndJsonStream` → `AgentSideConnection` → register `shutdown` on stdin end/close + SIGINT/SIGTERM (dispose sessions then exit 0) → swallow stdout 'error' so an early client close doesn't crash.

**Invariant:** A destroyed/non-writable stdout must never reject the ACP write path (the SDK's write promise resolves anyway); every teardown path must call `agent.dispose()` to kill owned pi subprocesses before exiting.

**Probe:** `test/unit/stdout-destroyed-does-not-crash.test.ts` ("stdout writer: resolves even if stdout is destroyed") — pins the destroyed-stdout tolerance.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-acp", query: "ndJsonStream AgentSideConnection", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the NDJSON stdio framing, the write-tolerant stdout wrapper, the `--terminal-login` spawnSync entrypoint, and the stdin-end/SIGINT/SIGTERM teardown that disposes sessions. Adapt the pi command resolution (`getPiCommand`) and the shell flag to the host. Omit the SDK's `AgentSideConnection`/`ndJsonStream` vendor internals (external dependency).

<!-- capsule-v2 -->
# Pi RPC transport — NDJSON request/response over the pi subprocess stdio

**Source:** pi-acp-jetbrain MIT `main@27aac05f`; Codebase Memory `pi-acp`. **Question:** How does the adapter speak pi's RPC protocol (newline-delimited JSON over stdio) — request/response correlation, prelude capture, ANSI stripping, and clean teardown?

## Pi RPC transport
**Path/Symbol:** `src/pi-rpc/process.ts:PiRpcProcess` (83-398).
**Signature:** `static PiRpcProcess.spawn(params: SpawnParams): Promise<PiRpcProcess>`; `proc.request(cmd: PiRpcCommand): Promise<PiRpcResponse>`; `proc.prompt/getState/getAvailableModels/setModel/...`.
**Data Shape:** Commands are typed unions (`{type:'prompt'|'abort'|'get_state'|'set_model'|'compact'|...}`), each stamped with a `crypto.randomUUID()` `id`; responses are `{type:'response', id, command, success, data?, error?}`. Non-JSON stdout lines before NDJSON starts are captured as `preludeLines` (human-readable Context/Skills/Extensions info).

### Decisive source
```ts
// spawn
const args = ['--mode', 'rpc', '--no-themes']
if (params.sessionPath) args.push('--session', params.sessionPath)
for (const ext of params.extensionPaths ?? []) args.push('--extension', ext)
const child = spawn(cmd, args, { cwd: params.cwd, stdio: 'pipe', env: {...process.env, ...params.env}, shell: shouldUseShellForPiCommand(cmd) })
// wait for 'spawn' or 'error'; ENOENT/EACCES -> PiRpcSpawnError with a helpful message
```
```ts
// request correlation
private request(cmd: PiRpcCommand): Promise<PiRpcResponse> {
  const id = crypto.randomUUID()
  const withId = { ...cmd, id }
  return new Promise((resolve, reject) => {
    this.pending.set(id, { resolve, reject })
    void this.writeLine(JSON.stringify(withId) + '\n').catch(error => { this.pending.delete(id); reject(error) })
  })
}
// readline 'line': JSON.parse; if !parseable -> stripAnsi + push to preludeLines
// if msg.type === 'response' && pending.has(id) -> resolve; else fan out to eventHandlers
```
```ts
// teardown ladder
async waitForExit(timeoutMs = 1_000): Promise<boolean> {
  if (this.child.exitCode !== null || this.child.signalCode !== null) return true
  this.dispose()                       // SIGTERM
  await Promise.race([this.exitPromise, sleep(timeoutMs)])
  if (this.child.exitCode !== null) return true
  this.child.kill('SIGKILL')           // force
  await Promise.race([this.exitPromise, sleep(500)])
  return this.child.exitCode !== null
}
```

**Flow:** spawn `pi --mode rpc --no-themes [--session <path>] [--extension <path>...]` → best-effort `getState` handshake (also `mkdirSync` the session-file parent dir to avoid later export parse errors) → each command gets a UUID id, written as one NDJSON line; the readline loop resolves the matching pending promise or fans the message out to `onEvent` handlers → on child exit/error, reject all pending → `dispose()` sends SIGTERM then SIGKILL with a bounded wait.

**Invariant:** Every RPC command carries a unique `id` and the response is correlated by that id; non-JSON stdout is treated as a prelude (never a protocol error); spawn failures surface as typed `PiRpcSpawnError` (ENOENT/EACCES) instead of later EPIPE noise; teardown escalates SIGTERM→SIGKILL and rejects all in-flight requests.

**Probe:** `test/unit/new-session-pi-not-found.test.ts` (spawn ENOENT → `PiRpcSpawnError` path) and `test/unit/pi-command.test.ts` (pi command resolution).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-acp", query: "PiRpcProcess spawn request pending", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the NDJSON request/response transport with UUID correlation, the `--mode rpc --no-themes` spawn args, prelude capture with ANSI stripping, and the SIGTERM→SIGKILL teardown ladder. Adapt the pi executable/args and the session-file parent-dir creation to the host. Omit the typed command union's host-specific members (e.g. `switch_session`) unless a target needs them.

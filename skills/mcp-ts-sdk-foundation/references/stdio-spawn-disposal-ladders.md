<!-- capsule-v2 -->
# Stdio client spawn & disposal ladders — how do you spawn and reap MCP server processes cross-platform without leaking pipes, hanging teardown, or inheriting a hostile environment?

**Source:** typescript-sdk MIT `main@3924de9`; Codebase Memory `typescript-sdk`. **Question:** What environment may a spawned MCP server inherit, what escalation order reaps it, and why does the internal dispose path await a different event than close()?

## Connected graph-selected seam
**Path/Symbol:** `packages/client/src/client/stdio.ts`: `DEFAULT_INHERITED_ENV_VARS`/`getDefaultEnvironment` (:54-94), `start` (:122-178), `stderr` getter (:187-193), `processReadBuffer` (:204-217), `_dispose` (:227-272), `close` (:274-313).
**Signature:** `async close(): Promise<void>`; `private async _dispose(): Promise<void>` (internal probe-sibling reaping)
**Data Shape:** env = {...getDefaultEnvironment(), ...serverParams.env}; ReadBuffer bounded by maxBufferSize (default 10 MB).

### Decisive source
```ts
// :85-88 — function-shaped values are an injection risk, skip them
if (value.startsWith('()')) { continue; }
// :279-309 — close(): stdin.end → race('close', 2000 unref'd) → SIGTERM → race → SIGKILL
await Promise.race([closePromise, new Promise(resolve => setTimeout(resolve, 2000).unref())]);
if (processToClose.exitCode === null) { kill('SIGTERM'); await race(...); }
if (processToClose.exitCode === null) { kill('SIGKILL'); }
// :230-250 + :252-270 — _dispose(): await 'exit' NOT 'close', then destroy PARENT pipes
const exited = new Promise<void>(resolve => proc.once('exit', () => resolve()));
proc.stdin?.end(); proc.kill('SIGTERM');
await Promise.race([exited, new Promise(resolve => setTimeout(resolve, 1000).unref())]);
...
proc?.stdout?.destroy(); proc?.stdin?.destroy(); proc?.stderr?.destroy();
```

**Flow:** constructor creates the stderr PassThrough immediately when piping was requested so
listeners attach BEFORE start() (early child output is never lost). spawn uses shell:false,
windowsHide on win32, merged env (defaults overridden by explicit serverParams.env). stdout data →
ReadBuffer.append → drain loop; overflow throws → onerror + close. close(): end stdin (polite
EOF), wait up to 2 s for the child 'close' event, escalate SIGTERM → 2 s → SIGKILL; onclose fires
from the child's 'close' handler, so it can never double-fire from close(). _dispose(): signal-first,
awaits 'exit' (a helper process holding inherited stdio pipes keeps 'close' pending forever),
then destroys the PARENT-side pipe handles — a flowing stdout 'data' listener would otherwise pin
the host event loop until the helper exits.

**Invariant:** teardown always has both a deadline and a last-resort signal, timers are unref'd so
teardown never keeps the loop alive by itself, and the read buffer is cleared on every path.
Environment inheritance is allowlist-only and pinned by a literal test so widening requires a
deliberate red-green change.

**Probe:** `packages/client/test/client/stdio.test.ts` :20-123 (clean close, message round-trip,
pid null after close, custom + default maxBufferSize overflow → onerror 'ReadBuffer exceeded
maximum size' + close), :125-152 (_dispose destroys parent-side handles even when a helper holds
the child stdio). `stdioEnvPins.test.ts` :46-68 (frozen safelist equality, unset keys skipped,
'() { echo pwned; }' PATH skipped). `crossSpawn.test.ts` :156-201 (windowsHide true on win32 /
false elsewhere).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "typescript-sdk", query: "StdioClientTransport getDefaultEnvironment _dispose SIGKILL unref", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt allowlist env inheritance with function-value skipping, the deadline+escalation reaping
ladder, and parent-pipe destruction in fast paths; adapt signals/timeouts to your OS surface;
omit cross-spawn only if you accept losing Windows .cmd resolution. Snippet verified via
get_code_snippet (close :274-313); coverage no_recorded_issue at the pin.

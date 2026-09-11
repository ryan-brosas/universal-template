<!-- capsule-v2 -->
# CLI server lifecycle — how does a stateless command get a stateful backend without a supervisor?

**Source:** pi-autoresearch-harness MIT `main@511760df8905c7b6e6bbd3a028de734becff69e6`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-autoresearch-harness`. **Question:** How does the CLI ensure the harness is up, and why does one action wait up to an hour for its HTTP response?

## ensure-up + postAction — detached spawn, 150×100ms readiness poll, 1h request timeout
**Path/Symbol:** `harness/cli.ts` — `isUp` :125–128, `startServer` :130–155, `postAction` :161–187, headers :114–119; server binds `127.0.0.1:$PI_AUTORESEARCH_PORT(9878)` (`server.ts:1573,1690`).
**Signature:** every action subcommand (and raw JSON passthrough) first `await startServer()` then POST `/action`; server mgmt via `--status/--start/--stop/--restart/--logs`.
**Data Shape:** response envelope `{ok:true, result:{text, details}} | {ok:false, error}`; identity headers `x-cwd` (URI-encoded) + optional `x-session-id` read from `.pi/autoresearch/session-id`.

### Decisive source
```ts
const child = spawnChild(process.execPath, [serverLauncher], {
  stdio: ['ignore','ignore','ignore'], detached: true, windowsHide: true,
});
child.unref();
for (let i = 0; i < 150; i++) {          // 100ms × 150 = 15s readiness budget
  await new Promise((r) => setTimeout(r, 100));
  if (await isUp()) return true;
}
// http.request timeout: 60 * 60 * 1000  — 'run' can benchmark for an hour
```

**Flow:** any CLI invocation → health GET → down ⇒ spawn detached launcher (survives CLI exit) → poll /health up to 15s → POST action with cwd/session headers → stream `result.text` to stdout or exit 1 with stderr error. Server holds ALL experiment state in memory per `cwd:sessionId`, so consecutive CLI calls form ONE continuous loop despite process-per-command.
**Invariant:** the long HTTP timeout is structural — `pi-autoresearch run` blocks synchronously until the benchmark finishes because the agent's next step depends on its output; killing the CLI mid-run would orphan a running benchmark. Detached+unref means the server outlives every client by design; `--stop` is the only sanctioned teardown (POST /quit). Status 0 from httpGet (connection refused) maps to "cannot reach harness server", never to a retry loop.
**Probe:** anchors: `grep -n 'i < 150' harness/cli.ts` → exactly :148; `grep -n "timeout: 60 \* 60 \* 1000" harness/cli.ts` → :78; `grep -n "readSessionIdFromFile\|x-cwd" harness/cli.ts | wc -l` → 3 (:102 def, :116 header, :115 x-cwd).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-autoresearch-harness", query: "startServer isUp postAction PI_AUTORESEARCH_PORT", limit: 10 });
```

## Verdict
Adopt lazy-daemon-ensure + synchronous long-poll action pattern verbatim when porting the loop to non-persistent hosts; adapt transport/port/env names; omit the Windows console-hide flags off-Windows. Coverage caveat: lifecycle untested directly — source-pinned.

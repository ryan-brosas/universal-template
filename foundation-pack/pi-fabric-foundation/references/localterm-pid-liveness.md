<!-- capsule-v2 -->
# Localterm session transport — how do you launch into a CLI session manager whose liveness is cheaper to check by PID than by re-invoking its binary?

**Source:** pi-fabric MIT `feat/veda-runner@4874ac3abefab27ee0064a3c8571ee017ceb3115`; Codebase Memory `pi-fabric`. **Question:** when an external session manager hands back both a session id and a child pid, which do you use for liveness, and how do you validate the launch handshake?

## JSON stdout handshake with pid-liveness and single-CLI-call discipline
**Path/Symbol:** `src/agents/transports/localterm-transport.ts` whole file (64L): class (:19-64), `LocaltermSession` (:14-17). Direct tests `tests/localterm-transport.test.ts` whole (68L).
**Signature:** `launch(request: AgentTransportLaunch): Promise<AgentTransportHandle>`; handle `{kind:"localterm", sessionId, attachCommand, livenessPollIntervalMs: 2_000, isAlive(), stop()}`.

### Decisive source
```ts
const command = `${await workerCommand(request.workerPath, request.workerArguments)}; exit $?`;
const { stdout } = await executeFile("localterm", [
  "session", "new", "--cwd", request.cwd, "--cmd", command,
  "--name", request.name, "--json",
]);
const session = JSON.parse(stdout) as LocaltermSession;
if (!session.id || !Number.isSafeInteger(session.pid) || session.pid <= 0)
  throw new Error("LocalTerm did not return a valid session");
// liveness WITHOUT spawning repeated LocalTerm CLI calls:
async isAlive() { return processIsAlive(session.pid); },
```

**Flow:** availability requires the binary on PATH AND a successful `localterm session ls --json` probe (3s timeout) — a bare `command -v` is insufficient because a broken install would pass. Launch composes the worker as a shell string (`workerCommand` shell-quotes each argv element) explicitly forwarding the worker's exit code (`; exit $?`), so the session's lifetime reflects the worker's. The `--json` response must carry BOTH a non-empty id and a positive safe-integer pid or the launch throws — no defaults. Stop shells out to `session kill <id>` (best-effort, swallow already-exited).
**Invariant:** after the ONE launch call, all liveness checks are local `process.kill(pid, 0)` probes — never repeated CLI invocations (the test's fake binary logs every call and asserts exactly ONE line after two isAlive polls); pid validation rejects negative/zero/unsafe integers so an unrelated recycled pid cannot be adopted blindly at launch time.
**Probe:** `bash -c 'cd /mnt/hdd/utopia/inspo/pi-ecosystem/pi-fabric && grep -n "processIsAlive(session.pid)" src/agents/transports/localterm-transport.ts | wc -l'` → 1 (:55); `grep -n "Number.isSafeInteger(session.pid)" src/agents/transports/localterm-transport.ts | wc -l` → 1 (:46); `grep -c "exit \$?" src/agents/transports/localterm-transport.ts` → 1; tests pin the single-call contract: log length stays 1 across two isAlive calls (`tests/localterm-transport.test.ts:59-63`) and stop emits `session kill session-1` (:66).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "LocaltermTransport session new json pid liveness", limit: 5, fields: ["signature", "name", "file"] });
```
(Rank #4 resolves `LocaltermTransport.launch` :32-63 line-exact.)

## Verdict
Adopt pid-based liveness for external session managers that expose their child pids, plus strict JSON-handshake validation at launch; adapt flags to your session CLI; omit the ls-probe availability gate if your binary fails fast on misuse. Fully direct-test-pinned via the fake-binary harness — no coverage caveat.

<!-- capsule-v2 -->
# Tmux/screen session twins — how do you launch detached workers into the two classic terminal multiplexers behind one handle contract, with per-multiplexer liveness probes?

**Source:** pi-fabric MIT `feat/veda-runner@4874ac3abefab27ee0064a3c8571ee017ceb3115`; Codebase Memory `pi-fabric`. **Question:** what differs between driving tmux and GNU screen for background agent sessions — creation flags, liveness probing, and teardown — and what must stay identical?

## Same session-name scheme, different probe/stop verbs per multiplexer
**Path/Symbol:** `src/agents/transports/tmux-transport.ts` whole file (53L): class (:15-53), `sessionName` (:13); `src/agents/transports/screen-transport.ts` whole file (45L): class (:11-45), `sessionName` (:9). Shared helpers: `src/agents/transports/process-utils.ts` (`executeFile` :9-33, `commandAvailable` :35-42, `workerCommand` :139-143, `scriptSpawnArgs` :130-137).
**Signature:** both `launch(request): Promise<AgentTransportHandle>` with `{kind:"tmux"|"screen", sessionId: "pi-fabric-<id.slice(0,12)>", attachCommand, livenessPollIntervalMs: 2_000, isAlive(), stop()}`.

### Decisive source
```ts
// tmux: worker as a SHELL COMMAND string; liveness = has-session exit code
await executeFile("tmux", ["new-session", "-d", "-s", session, "-c", request.cwd,
  await workerCommand(request.workerPath, request.workerArguments)]);
async isAlive() { try { await executeFile("tmux", ["has-session", "-t", session]); return true; }
                   catch { return false; } },
// screen: worker as an ARGV script-spawn; -DmS detaches + logs the dead session;
// liveness = STRING MATCH on screen -ls output (two accepted shapes)
await executeFile("screen",
  ["-DmS", session, ...(await scriptSpawnArgs(request.workerPath, request.workerArguments))],
  { cwd: request.cwd });
const { stdout } = await executeFile("screen", ["-ls"]);
return stdout.includes(`.${session}`) || stdout.includes(`\t${session}`);
```

**Flow:** availability = `commandAvailable(<binary>)` via `sh -lc 'command -v …'` with a 2s timeout. Session names share the `pi-fabric-<12-char-id-prefix>` scheme across both backends (and herdr/localterm use their own id vocabularies), so attach hints are unambiguous. Creation differs structurally: tmux receives the fully-quoted command STRING as its shell argument (`workerCommand`), while screen takes `[runtime, worker.js, …]` argv elements after `-DmS` (`scriptSpawnArgs`) and relies on `-DmS` to detach without a controlling terminal. Teardown: tmux `kill-session -t`, screen `-S <name> -X quit` — both best-effort swallows of already-exited sessions.
**Invariant:** every isAlive failure path resolves FALSE rather than throwing — a transient CLI error must read as "dead" to the supervisor's sustained-dead window (see `agent-runtime-and-retry`), never crash the monitor loop; screen's string-scan liveness accepts BOTH the `.name` (attached) and `\tname` (detached) column shapes because screen's `-ls` output format varies by state; the advertised 2s poll interval tells the manager to poll these CLI-based backends slower than the process transport's 250ms.
**Probe:** `bash -c 'cd $REFERENCE_ROOT/pi-ecosystem/pi-fabric && grep -n "has-session" src/agents/transports/tmux-transport.ts | wc -l'` → 1 (:40); `grep -n 'stdout.includes' src/agents/transports/screen-transport.ts | wc -l` → 1 (:33, BOTH column shapes accepted on that single line); `grep -n '"-DmS"' src/agents/transports/screen-transport.ts | wc -l` → 1 (:22); `grep -c 'pi-fabric-' src/agents/transports/tmux-transport.ts` → 1 and same for screen (one sessionName per file).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "TmuxTransport ScreenTransport launch has-session detach", limit: 5, fields: ["signature", "name", "file"] });
```
(Rank #1-2 resolve `TmuxTransport.launch` :22-52 and `ScreenTransport.launch` :18-44 line-exact.)

## Verdict
Adopt the shared naming scheme + fail-soft isAlive + advertised slow poll interval for any CLI-driven session backend; adapt creation style to each tool's grammar (string command vs argv splice) instead of forcing one shape; omit the screen dual-shape scan if your screen version has stable output. Coverage caveat: these two backends have no dedicated upstream specs (the family adapter test covers selection only) — probes are source-derived.

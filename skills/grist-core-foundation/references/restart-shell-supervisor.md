<!-- capsule-v2 -->
# RestartShell socket-passing supervisor — how does a zero-downtime restart keep the listening port while the worker process is replaced (or crashes)?

**Source:** grist-core Apache-2.0 `main@c057666bb93b6f93a69b0884ce023676c3a2804b`; Codebase Memory `grist-core`. **Question:** What FSM and socket-forwarding contract let a parent own the public port across child restarts, and which failures deliberately take the whole shell down?

## Shell owns the TCP listener; connections hand off via IPC; unexpected child death kills the shell — it is NOT a general process manager
**Path/Symbol:** `app/server/lib/RestartShell.ts` — `ShellStatus` FSM (:77–82), `_createPublicServer` (:245–258), `_fallbackResponse` (:276–283), `_forkWorker` (:307–346), `_spawnOrFail` (:387–427), `shouldRunAsRestartShell()` (:451–461), `Deps.unhealthyTimeoutMs = 15000` (:63–68).
**Signature:** `start()/listen()/run(): Promise<void>`; `restart()/shutdown(killSig = "SIGTERM"): Promise<void>` (serialized on a PromiseChain); `_stopChild(child, exited, sig, timeoutMs = 10000)`.
**Data Shape:** Status union: `starting → running{child, exited} → restarting → running | stopping → stopped`; failed spawn sets non-zero exitCode + queued shutdown. Fork env: `GRIST_UNDER_RESTART_SHELL: "1"`, `PORT: <actual>`, and `delete env.GRIST_RESTART_SHELL` so the child can't re-detect shell mode (:314–318).

### Decisive source
```ts
// RestartShell.ts:245-257 — accept with pauseOnConnect, forward raw socket over IPC or answer locally
return net.createServer({ pauseOnConnect: true }, (socket) => {
  this._connections.add(socket);
  socket.on("close", () => this._connections.delete(socket));
  const forwardTo = this._childIfForwardable();     // running AND child.connected (dead-channel window guard)
  if (forwardTo) {
    this._forwardSocketToChild(forwardTo, socket);  // c.send({action:"connection"}, socket)
  } else {
    this._fallbackServer.emit("connection", socket); // unbound http.Server answers /status
    socket.resume();
  }
});
```

**Flow:** `listen()` binds the port FIRST (`/status` reachable, fallback answers 503 "starting") → `run()` spawns child; ready = first IPC `{action:"ready"}` → running. Every accepted connection: forward to live child via `child.send(msg, socket)`; send-error destroys the socket ("client would otherwise hang with no reader"). Fallback ladder for non-/status or degraded states: RESTARTING/STARTING 503 JSON, UNHEALTHY 500 plain, `/status?ready=1` NOT_READY 500 until child reports alive. Restarts serialize through the ops chain; `_doShutdown` destroys pending sockets, calls `server.close()` WITHOUT awaiting (handed-off fds would hold the count until the child closes them — synchronous stop-accepting is all that's needed, :211–215 comment). Crash policy: pre-ready exit rejects `ready` and records the spec key for re-resolution; POST-ready unexpected exit ⇒ `process.exitCode = code` and shell shutdown (:348–363). Watchdog: spawn stalls >15s flip `_healthy=false` for orchestration; child `busy` heartbeats reset the timer and restore health (:387–400).
**Invariant:** The shell exits when its child dies unexpectedly — deliberate single-child supervision, not a supervisor tree. Spec-failure fallback: failed keys accumulate in `_failedSpawnKeys`; resolver re-consulted on EVERY fork; retry loop ends only when the re-resolved spec has the SAME key as the failed one (`forkSpecKey = key ?? entryPoint`). Activation gate `shouldRunAsRestartShell()`: never recurse under shell; explicit env wins; OFF when `GRIST_TESTING_SOCKET` set (tests SIGSTOP the process — pausing only the shell while a worker serves would break pauseUntil()); default ON only for plain Linux node, not Electron.
**Probe:** `test/server/lib/RestartShell.ts` (:80 /status+ready matrix, :91 not-alive during startup, :123 initial-spawn-fail sets exitCode 7-propagation, :143 shutdown-after-in-flight-restart serialization, :173 slow-restart unhealthy→recover, :196 busy-heartbeat keeps healthy, :239/:253 spec-key fallback incl. same-entrypoint-distinct-key, :271 keep-alive rerouting after restart, :300 documents after 3 restarts, :319 WebSocket survival). Source pins: `grep -n 'pauseOnConnect' app/server/lib/RestartShell.ts` = :246; `grep -c 'unhealthyTimeoutMs' app/server/lib/RestartShell.ts` = 4.

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project":"grist-core","query":"RestartShell fork worker ready connection fallback unhealthy","limit":10,"detail":"ids"}'
```

## Verdict
Adopt port-owning parent + IPC socket passing + the five-state FSM + fail-fast crash coupling + busy-heartbeat health model; adapt signal handling to your init system (grist caps cleanup at 15s and exits 128+signum for container pid-1 contracts); omit Electron/Windows caveats unless targeting them. Direct mocha coverage at this pin (real forks, real sockets); runner-blocked locally — probes recorded as source-pinned assertions.

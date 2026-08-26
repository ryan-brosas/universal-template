<!-- capsule-v2 -->
# connector-supervisor-restart — how does one authority own detached child lifecycles across hub restarts without ever double-running or ghosting an instance?

**Source:** Cline Apache-2.0 `main@4f836ae7d0ed29ece7ef4a2a478deb470fdd056e`; Codebase Memory `cline`. **Question:** What does a correct supervisor for long-lived detached connectors look like — restart policy, stop semantics, adoption of survivors, and the races between start/stop/exit-cleanup?

## Per-instance lock tails; exponential give-up ladder; mark-before-signal; generation-checked cleanup
**Path/Symbol:** `sdk/packages/core/src/services/connectors/connector-supervisor.ts` (`ConnectorSupervisor` :124-664; constants :24-40; `withInstanceLock` :226-240; `startLocked` :249-289; `stopLocked` :302-333; `handleExit` :458-502; `scheduleRestart` :504-552; `adoptRunningConnectors` :188-217). Singleton via module-level `activeSupervisor` (:666-682) because per-request handlers have no other shared state.
**Signature:** `start({channel, instanceId, args, restart}) → {started, reason?, record}`; `stop({channel, instanceId, disableAutostart?}) → boolean`; key = `channel + "\u0000" + instanceId` (NUL join cannot collide).
**Data Shape:** SupervisedEntry{state: running|backoff|failed|stopped, origin: spawned|adopted, argsKnown, pid?, child?, restarts, nextRestartAt?, lastExit*}; deps injected for testability (spawnProcess, isProcessRunning, killProcess, now, setTimer/clearTimer). Constants: BASE 1_000ms, MAX 60_000ms, GIVE_UP_AFTER 5, COUNTER_RESET_MS 60_000, ADOPTED_POLL 5_000ms, SIGTERM wait 5_000ms, SIGKILL wait 2_000ms.

### Decisive source
```ts
// One instance, one queue — both start and stop suspend mid-flight:
private withInstanceLock<T>(key: string, task: () => Promise<T>): Promise<T> {
	const previous = this.instanceLocks.get(key) ?? Promise.resolve();
	const run = previous.then(task, task);          // run regardless of prior outcome
	const tail = run.then(() => undefined, () => undefined);
	this.instanceLocks.set(key, tail);              // tail swallows errors so chain never poisons
	void tail.then(() => { if (this.instanceLocks.get(key) === tail) this.instanceLocks.delete(key); });
	return run;
}
// Restart ladder with healthiness reset and give-up:
if (entry.restarts >= RESTART_GIVE_UP_AFTER) { entry.state = "failed"; /* log */ return; }
const delayMs = Math.min(RESTART_BASE_DELAY_MS * 2 ** entry.restarts, RESTART_MAX_DELAY_MS);
// ...in handleExit first: a run >= RESTART_COUNTER_RESET_MS clears entry.restarts to 0

// Mark-before-signal stop (exit handler checks state=="stopped" and stands down):
entry.state = "stopped";
if (pid && this.isProcessRunning(pid)) {
	this.signal(pid, "SIGTERM");
	if (!(await this.waitForProcessExit(pid, STOP_SIGTERM_TIMEOUT_MS))) {   // replacement must not
		this.signal(pid, "SIGKILL");                                        // race a live port holder
		await this.waitForProcessExit(pid, STOP_SIGKILL_TIMEOUT_MS);        // (EADDRINUSE crash loop)
	}
}
// Generation check after ANY await in an exit path:
if (this.disposed || entry.state === "stopped" || this.entries.get(key) !== entry) return;
```

**Flow:** start → instanceLock → alive&&!restart ⇒ already_running | alive&&restart ⇒ stopLocked then fresh spawn | dead entry ⇒ cancelRestart + retire explicitly (state=stopped, removeAllListeners("exit")) so pending backoff timers/in-flight cleanups stand down → spawnEntry sets CLINE_CONNECTOR_SUPERVISED_ENV=1 on child env, detached:true but listener NOT unref'd | exit (child event) or poll (adopted only, no child handle) → handleExit → healthiness reset → cleanup → identity+state re-check → autostart gate → scheduleRestart (timer fires UNDER the instance lock and re-checks identity) | stop → disableAutostart (default true) → mark-before-signal → TERM/KILL ladder → cleanup → delete.
**Invariant:** The in-memory map is the single authority on which connector processes may run — two processes can never hold the same bot token via a state-file race. Every async gap in exit/restart paths re-validates (disposed | stopped | map[key]===entry). Adopted entries carry argsKnown=false: emptiness never encodes "unknown argv"; their restart args come from the persisted autostart record or the restart fails. dispose() stops supervising WITHOUT killing — children are deliberately detached to outlive this hub and be adopted by the next.
**Probe:** `grep -cF 'export const RESTART_GIVE_UP_AFTER = 5;' …connector-supervisor.ts` → 1; `grep -cF 'existing.state = "stopped";' …` → 1; `grep -cF 'this.entries.get(key) !== entry' …` → 2 (handleExit + timer); `grep -cF 'RESTART_BASE_DELAY_MS * 2 ** entry.restarts,' …` → 1; test pins: "serialises a boot-time restart with a concurrent user start", "does not schedule a restart for an entry replaced while its cleanup was in flight", "clears the restart counter after a run that stayed up", "adopts connectors that predate this hub and polls them for death" — all present. All executed pre-write, exit 0.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "cline", qualified_name: "cline.sdk.packages.core.src.services.connectors.connector-supervisor.ConnectorSupervisor.withInstanceLock" });
// observed: Method, lines 226-240, source returned verbatim matching excerpt above
```

## Verdict
Adopt: per-key promise-tail serialization, mark-before-signal stops that WAIT for death before replacement, exponential restart with consecutive-failure give-up plus healthy-run counter reset, generation-checked post-await continuation, adopt-by-pid with dual exit detection (events vs polling), and dispose-without-kill. Adapt all timeout constants and the cleanup delegation (Cline delegates domain cleanup — state files/thread bindings/sessions — to the CLI host). Omit connector-store specifics. Runner-BLOCKED here; probes green.

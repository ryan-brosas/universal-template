<!-- capsule-v2 -->
# shutdown-coordinator-monotonic — how does a process guarantee exactly-once cleanup while exit codes only ever escalate and a hung cleanup cannot wedge it?

**Source:** Cline Apache-2.0 `main@4f836ae7d0ed29ece7ef4a2a478deb470fdd056e`; Codebase Memory `cline`. **Question:** How do you merge many shutdown triggers (signals, drain, retire) into one monotonic lifecycle where cleanup runs once, fatal triggers raise the exit code but never re-run cleanup, and a deadline force-exit still respects observer failures?

## One shared cleanup promise; max() escalation; referenced watchdog; try/finally forced exit
**Path/Symbol:** `sdk/packages/core/src/hub/daemon/shutdown-coordinator.ts` (`createHubDaemonShutdownCoordinator` :40-125; `HUB_DAEMON_SHUTDOWN_DEADLINE_MS = 2_000` :5).
**Signature:** `createHubDaemonShutdownCoordinator({deadlineMs, cleanup(): Promise<void>, exit(code): void, onCleanupError?, onForcedExit?}) → {request({reason, exitCode}): Promise<void>, force(request): void, getState(): idle|shutting_down|forced|finished}`.
**Data Shape:** Request carries a reason string + exitCode; requestedExitCode persists across requests and only escalates via Math.max. The deadline constant is deliberately BELOW the retire-ladder caller-side wait so the current daemon exits through its own cleanup before an older caller considers force retirement (pinned by test).

### Decisive source
```ts
const request = (shutdownRequest) => {
	requestedExitCode = Math.max(requestedExitCode, shutdownRequest.exitCode);
	if (shutdownPromise) return shutdownPromise;      // every graceful trigger shares ONE cleanup
	state = "shutting_down";
	watchdog = setTimeout(() => force({reason: `shutdown deadline exceeded after ${shutdownRequest.reason}`, ...}), options.deadlineMs);
	// Keep the watchdog referenced. If every other handle disappears while a fatal
	// cleanup promise is still pending, natural process exit could report code 0
	// instead of the requested failure code.
	shutdownPromise = (async () => { try {
		// Defer invocation one microtask so `shutdownPromise` is assigned
		// before cleanup can synchronously re-enter `request()`.
		await Promise.resolve().then(() => options.cleanup());
	} catch (error) { requestedExitCode = Math.max(requestedExitCode, 1); options.onCleanupError?.(error);
	} finally { clearTimeout(watchdog); if (state === "shutting_down") { state = "finished"; requestExit(requestedExitCode); } } })();
	return shutdownPromise;
};
const force = (request) => {
	requestedExitCode = Math.max(requestedExitCode, request.exitCode);   // escalate even when already forcing
	if (state === "forced" || state === "finished") return;
	state = "forced"; clearTimeout(watchdog);
	try { options.onForcedExit?.({...request, exitCode: requestedExitCode}); }
	finally { /* hook failure must never disarm the watchdog / strand forced */ requestExit(requestedExitCode); }
};
const requestExit = (code) => { if (exitRequested) return; exitRequested = true; options.exit(code); };  // once-only exit
```

**Flow:** first graceful request ⇒ state=shutting_down + watchdog armed + cleanup promise created and returned (later requests get the SAME promise, code escalated) → cleanup success ⇒ finished+requestExit | cleanup throw ⇒ code≥1 + onCleanupError + still finishes | deadline fires or second signal calls force ⇒ state=forced, onForcedExit in try/finally, single guarded exit | injected exit() that returns cannot be retried (exitRequested latch).
**Invariant:** Cleanup runs at most once per process no matter how triggers interleave or re-enter; exit code is monotonic non-decreasing; the forced path exits even when observers throw; the deadline ordering (daemon 2s < caller-side retirement wait) prevents an old caller from SIGKILLing a daemon that was about to finish its own graceful exit.
**Probe:** `grep -cF 'export const HUB_DAEMON_SHUTDOWN_DEADLINE_MS = 2_000;' …` → 1; `grep -cF 'requestedExitCode = Math.max(requestedExitCode,' …` → 3 (request, force, cleanup-error); `grep -cF 'await Promise.resolve().then(() => options.cleanup());' …` → 1; test pins: "upgrades the exit code when a fatal request arrives during cleanup", "does not re-enter cleanup when cleanup requests shutdown", "still exits when the forced-exit observer throws", "keeps the daemon deadline below the caller-side retirement wait" — all present in shutdown-coordinator.test.ts. All executed pre-write, exit 0.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "cline", qualified_name: "cline.sdk.packages.core.src.hub.daemon.shutdown-coordinator.createHubDaemonShutdownCoordinator" });
// observed: Function lines 40-125 returned verbatim incl. both decisive comments
```

## Verdict
Adopt the whole closure: shared-cleanup-promise idempotence, max()-only escalation, referenced watchdog, once-latched exit, try/finally around forced-exit hooks, microtask defusal of synchronous re-entry, and deadline-below-retire-wait ordering. Adapt the deadline value to host retirement timeouts (keep the inequality), keep reason strings in the request for diagnostics. Omit Cline's hub wiring. Runner-BLOCKED here; probes green.

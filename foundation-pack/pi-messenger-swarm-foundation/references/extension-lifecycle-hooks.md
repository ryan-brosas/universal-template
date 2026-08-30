<!-- capsule-v2 -->
# Extension lifecycle hooks — which pi events wire the messenger together and in what order?

**Source:** pi-messenger-swarm MIT `main@6fe429a4b74ae276a621bb72910d7926fb6b3104`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-messenger-swarm`. **Question:** What does each registered hook own, and what must run even without auto-register?

## session_start bootstrap / turn_end accounting / shutdown janitorship
**Path/Symbol:** `index.ts:piMessengerExtension` — session_start #1 (:307-370), session_start #2 resume/fork (:376-383), turn_end (:390-408), session_shutdown (:415-432), tool_call reservation hook (:434-436), 15s status heartbeat (:131-146).
**Signature:** `export default function piMessengerExtension(pi: ExtensionAPI)` — factory closing over per-session state.
**Data Shape:** legacy feed cleanup `rm ~/.pi/agent/messenger/feed.jsonl` best-effort; harness started unless PI_SWARM_SPAWNED.

### Decisive source
```ts
// Start the harness server even without auto-register —
// the model needs it for CLI actions regardless.
if (!process.env.PI_SWARM_SPAWNED) {
  harnessServer.start();
}
...
pi.on('session_shutdown', async () => {
  stopAllSpawned(cwd);        // safety net for extension-spawned agents only
  stopStatusHeartbeat();
  // Do NOT send /quit to the harness server on session shutdown.
  ...the harness handles agent cleanup via its own session tracking...
  harnessServer.stop();       // Only stops the process WE spawned (if any)
  await handleSessionShutdown(state, dirs);
  activityTracker.dispose();
});
```

**Flow:** startup: heartbeat on → stale-feed rm → rebind → session-id file → alias install → harness start (non-subagents) → optional auto-register (config flag OR path glob match) with prune+join event + registration context message. turn_end: usage tokens accumulate → trailing registry flush. Second session_start handles ONLY new/resume/tree reasons (skips startup/reload). Shutdown order: kill own spawns → stop heartbeat → stop own harness process → unclaim choreography → dispose timers.
**Invariant:** Two hooks share the 'session_start' name distinguished by `event.reason` — merging them breaks reload semantics. The daemon-outlives-sessions rule means extension stop() only reaps a child IT spawned this session; the shared detached server persists deliberately.
**Probe:** `grep -c "pi.on('session_start'" index.ts` (=2); `grep -c "PI_SWARM_SPAWNED" index.ts` (=2); direct test coverage via `tests/swarm/session-shutdown-cleanup.test.ts::should unclaim all tasks when agent leaves` (:18).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-messenger-swarm", query: "session_start session_shutdown turn_end autoRegister harnessServer startStatusHeartbeat", limit: 8 });
```

## Verdict
Adopt the hook ownership map and the always-start-daemon-even-without-auto-register rule; adapt event names to your host API; preserve the reason-split if your host distinguishes resume from reload.

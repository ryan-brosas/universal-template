<!-- capsule-v2 -->
# env-sentinel-claim — how does a process carry "what I am" to itself without leaking it to every child it spawns?

**Source:** Cline Apache-2.0 `main@4f836ae7d0ed29ece7ef4a2a478deb470fdd056e`; Codebase Memory `cline`. **Question:** How do you mark a process as daemon/supervised via environment when that same environment is inherited by everything the process spawns (shell commands, MCP servers, hooks), and when must a marker propagate instead of being scrubbed?

## Claim-once latched sentinels; propagation-only markers
**Path/Symbol:** `sdk/packages/shared/src/runtime/hub-daemon-env.ts` (`claimHubDaemonProcess` :41-47, `isHubDaemonProcess` :57-66, `claimSupervisedConnectorProcess` :91-98, `isSupervisedConnectorProcess` :113-123, `setStartingConnectorInstance` :136-141, `readStartingConnectorInstance` :143-164).
**Signature:** `claimHubDaemonProcess(env = process.env): boolean` — reads sentinel, latches, deletes; `isHubDaemonProcess(env?: Env): boolean` — explicit env read verbatim, else latch first, then process.env.
**Data Shape:** Sentinel value is exactly `"1"`; latch is module-level `boolean | undefined` (undefined = not claimed yet). Starting-instance marker is JSON `{channel, instanceId}` (ConnectorInstanceRef); readers parse defensively and return undefined on any malformation.

### Decisive source
```ts
export function claimHubDaemonProcess(
	env: Record<string, string | undefined> = process.env,
): boolean {
	claimedHubDaemonProcess = env[CLINE_RUN_AS_HUB_DAEMON_ENV] === "1";
	delete env[CLINE_RUN_AS_HUB_DAEMON_ENV];   // scrub BEFORE spawning anything
	return claimedHubDaemonProcess;
}
// ...the documented failure it prevents:
//   An inherited sentinel makes each child try to become a hub daemon instead
//   of running the command, and they die on EADDRINUSE against the real hub.
//   Observed as every `cline` invocation from a Slack connector agent failing,
//   `cline --help` included, because personality is chosen before argument parsing.

// The marker that must NOT be scrubbed (propagates into the spawned daemon):
//   The instance doing the starting is not yet registered as active when the
//   daemon boots, so without this marker the daemon launches a second copy of
//   it - two processes holding the same bot token.
export function setStartingConnectorInstance(ref: ConnectorInstanceRef, env = process.env): void {
	env[CLINE_CONNECTOR_STARTING_INSTANCE_ENV] = JSON.stringify(ref);
}
```

**Flow:** entrypoint calls claim* once → latch remembers the answer for this process forever → sentinel removed from env so agent-spawned grandchildren cannot re-enter the wrong personality | is*(env?) with an EXPLICIT env ignores the latch (child environments are judged verbatim) | spawn paths that deliberately start a daemon/connector set the sentinel explicitly on the CHILD env, so claiming never breaks legitimate nesting | starting-instance marker flows parent→daemon by inheritance and is consumed by the daemon's reconnect logic.
**Invariant:** A personality marker must be consumed exactly once at the boundary that acts on it; after claim, the process's identity survives only in memory, never in inheritable state. Read-back precedence: explicit-env > latch > ambient env. Defensive readers never throw — malformed markers are absent markers.
**Probe:** `grep -cF 'delete env[CLINE_RUN_AS_HUB_DAEMON_ENV];' sdk/packages/shared/src/runtime/hub-daemon-env.ts` → 1; `grep -cF 'let claimedSupervisedConnectorProcess: boolean | undefined;' …` → 1; `grep -cF 'two processes holding the same bot token' …` → 1; direct test pin: connector-supervisor.test.ts case "strips daemon and connector-child markers from the child environment" → present. All executed pre-write, exit 0.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "cline", query: "claim supervised connector process restart", file_pattern: "*hub-daemon-env*", limit: 10 });
// observed: total 10, top hits claimSupervisedConnectorProcess :91-98,
// isSupervisedConnectorProcess :113-123, ConnectorInstanceRef :14-17; has_more false
```

## Verdict
Adopt claim-once latch + delete semantics for any env-carried role marker whose process also spawns children, and the explicit-env-beats-latch read order. Adopt the propagation-only counter-marker pattern whenever a parent must tell its own spawned authority "I am the one starting you". Adapt variable names and the JSON marker schema to host vocabulary; keep defensive undefined-on-malformed readers. Omit Cline's specific CLI personalities. Runner-BLOCKED here; probes green.

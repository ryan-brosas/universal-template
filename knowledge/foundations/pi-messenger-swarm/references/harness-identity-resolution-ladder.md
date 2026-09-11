<!-- capsule-v2 -->
# Harness identity resolution ladder — how does one shared server know WHICH agent sent a request?

**Source:** pi-messenger-swarm MIT `main@6fe429a4b74ae276a621bb72910d7926fb6b3104`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-messenger-swarm`. **Question:** What is the exact precedence for resolving caller identity, and why does each rung exist?

## name header → pid header → single/most-recent fallback
**Path/Symbol:** `harness/server.ts:resolveAgentState` (:172-376, docblock :157-171), headers read at :527-534 (`x-agent-name`, `x-caller-pid`, `x-session-id`, `x-messenger-channel`, `x-caller-cwd`); CLI-side `harness/cli.ts:agentHeaders` (:249-286).
**Signature:** `resolveAgentState(dirs, callerPid?, agentName?, channelHint?, requestSessionId?): { state, resolvedCwd }`.
**Data Shape:** state rebuilt FROM DISK per request (server is stateless per call); unregistered-but-named agents keep their name with `registered=false`.

### Decisive source
```ts
// Strategy 2: match by caller PID (legacy fallback)
// Skip if an explicit agent name was provided but not found —
// we'd rather preserve the explicit name than match by PID.
if (!registered && !agentName && callerPid) {
```
```ts
// CLI priority: env var (subagents) > registration file (coordinator) > pid walk (last resort)
const envName = process.env.PI_AGENT_NAME?.trim();
if (envName) headers['x-agent-name'] = envName;
else { const regName = readRegistrationName(); if (regName) headers['x-agent-name'] = regName; }
```

**Flow:** strategy 1 matches registration by `name`; on miss the name is PRESERVED with registered=false so executeJoin takes the fresh-registration path honoring the channel hint. Strategy 2 (pid) is skipped whenever an explicit name was given — a stale pid must never override intent. Strategy 3: one registration ⇒ use it; many ⇒ most-recent mtime wins. Session mismatch then clears ONLY sessionChannel (+ currentChannel if it pointed at it), never joinedChannels.
**Invariant:** The comment-documented wild failure this prevents: coordinator joins #channel, spawns agents, harness restarts, session-id changes → wiping currentChannel would silently reroute feed/task calls to the wrong channel. The channelHint applies to currentChannel ONLY for unregistered agents (spawned children inheriting PI_MESSENGER_CHANNEL); registered agents' switches go through action bodies.
**Probe:** direct tests `tests/swarm/join-channel-inheritance.test.ts::preserves the pre-set channel when joining unregistered (simulates resolveAgentState from x-messenger-channel header)` (:80), `::respects explicit --channel flag over pre-set channel` (:151), `tests/swarm/per-request-project.test.ts::caller cwd takes priority over server startup cwd for project resolution` (:175); `grep -c "Strategy 2: match by caller PID" harness/server.ts` (=1).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-messenger-swarm", query: "resolveAgentState agentHeaders findCallerPid x-agent-name x-caller-pid", limit: 6 });
```

## Verdict
Adopt the three-rung ladder and especially the "explicit-name-not-found beats pid" rule plus session-mismatch partial reset; adapt header names; omit the pid process-tree walk (`ps` scraping) if your host always sets an identity env var.

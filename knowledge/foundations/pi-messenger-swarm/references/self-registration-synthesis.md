<!-- capsule-v2 -->
# Whois/list self-registration synthesis — how does an agent render its OWN presence row without a registry roundtrip?

**Source:** pi-messenger-swarm MIT `main@6fe429a4b74ae276a621bb72910d7926fb6b3104`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-messenger-swarm`. **Question:** How are list/whois output lines built for peers vs self?

## buildSelfRegistration + shared formatAgentLine
**Path/Symbol:** `lib/status.ts:buildSelfRegistration` (:83-109), `agentHasTask` (:111-118); `handlers/coordination/list.ts:formatAgentLine` (:36-82) + self line (:87-89); `whois.ts:executeWhoisSelf` (:53-63).
**Signature:** `buildSelfRegistration(state): AgentRegistration` — throws when no current/session channel set.
**Data Shape:** synthetic registration carries `pid: process.pid`, `sessionId: ''`, live session counters; peer rows come straight from registry files.

### Decisive source
```ts
const currentChannel = state.currentChannel || state.sessionChannel;
if (!currentChannel) {
  throw new Error('No current or session channel set');   // fail loud, never guess a channel
}
...
return {
  name: state.agentName, pid: process.pid, sessionId: '', cwd: process.cwd(), ...
};
```
```ts
const hasTask = agentHasTask(agent.name, sessionTasks);   // assigned_to|claimed_by ∧ in_progress
```

**Flow:** both list and whois compute hasTask per agent by scanning REPLAYED session tasks (claimed_by OR legacy assigned_to match ∧ in_progress) so the presence line's active/idle/stuck classification reflects work-holding; self uses the synthesized record through the SAME formatter, guaranteeing identical column semantics.
**Invariant:** The throw-on-no-channel guard protects downstream `displayChannelLabel('')` garbage — porters who soften it to a default string mask broken join state. Self rows intentionally report `sessionId: ''` because in-process callers know their own context; disk registrations are only consulted for OTHERS.
**Probe:** direct tests `tests/swarm/channels.test.ts::returns not_registered error when not registered` (:230) covers gating; `grep -c "buildSelfRegistration" lib/status.ts handlers/coordination/list.ts handlers/coordination/whois.ts` (1 each); `grep -n "assigned_to === name || t.claimed_by === name" lib/status.ts`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-messenger-swarm", query: "buildSelfRegistration agentHasTask formatAgentLine executeWhoisSelf", limit: 5 });
```

## Verdict
Adopt self-synthesis through one shared formatter plus task-aware presence inputs; adapt columns; keep the loud no-channel throw.

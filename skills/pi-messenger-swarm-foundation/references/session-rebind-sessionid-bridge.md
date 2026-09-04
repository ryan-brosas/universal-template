<!-- capsule-v2 -->
# Session rebind + session-id file bridge — how do CLI children and resumed sessions agree on WHICH pi session is live?

**Source:** pi-messenger-swarm MIT `main@6fe429a4b74ae276a621bb72910d7926fb6b3104`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-messenger-swarm`. **Question:** How is the in-process session id exported to out-of-process callers, and how does a live messenger survive session switches?

## session-id file + rebindContextSession + effective-session fallback
**Path/Symbol:** `index.ts:session_start` writer (:317-335, PI_SWARM_SPAWNED guard :328), `store/shared.ts:getEffectiveSessionId` (:118-127) + `getProjectChannelSessionId` (:93-109), `store/registration.ts:rebindContextSession` (:307-353).
**Signature:** `rebindContextSession(state, dirs, ctx): RebindContextSessionResult`; `getEffectiveSessionId(cwd, state): string`.
**Data Shape:** `<cwd>/.pi/messenger/session-id` (plain text); channel header `sessionId` field as alternate source.

### Decisive source
```ts
// IMPORTANT: Skip for spawned subagents (PI_SWARM_SPAWNED=1).
// Subagents share the same project directory as the parent, so
// writing their session ID would overwrite the parent's file.
if (sessionId && !process.env.PI_SWARM_SPAWNED) {
  fs.writeFileSync(sessionFilePath, sessionId, 'utf-8');
}
```
```ts
export function getEffectiveSessionId(cwd: string, state: MessengerState): string {
  const currentChannel = state.currentChannel ?? state.sessionChannel;
  if (currentChannel) {
    const channelSessionId = getProjectChannelSessionId(cwd, currentChannel);
    if (channelSessionId) return channelSessionId;   // parent and child converge here
  }
  return state.contextSessionId ?? '';
}
```

**Flow:** extension writes session-id at session_start (parent only); CLI reads it per-invocation into `x-session-id`; server patches registration/channel headers when it discovers an id later (`patchChannelSessionId`). On resume/switch inside one process, `rebindContextSession` fires when env-inherited channel exists without a sessionChannel OR context id changed: ensureStateChannels → leave event on old channel → join on new.
**Invariant:** The spawned-subagent write-skip prevents the classic orphan-channel bug documented in-source: a child overwriting session-id makes the NEXT parent CLI call see a "session mismatch" and mint a spurious channel. Effective-session resolution prefers the CHANNEL's stored id so parent and all children share ONE task-store namespace regardless of which process performs an action.
**Probe:** direct tests `tests/swarm/spawn-channel-inheritance.test.ts::passes the parent channel to spawned agents via environment` (:77 pins `env.PI_MESSENGER_CHANNEL === 'session-parent'` AND `env.PI_SWARM_SPAWNED === '1'`), `tests/swarm/per-request-project.test.ts::project B agent can find its channels even when server started from project A`; `grep -c "PI_SWARM_SPAWNED" index.ts` (=2).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-messenger-swarm", query: "rebindContextSession getEffectiveSessionId patchChannelSessionId session-id", limit: 6 });
```

## Verdict
Adopt the file-bridge + skip-for-spawned guard + channel-scoped effective-session convergence; adapt paths; omit rebind UI events if your host cannot hot-switch sessions in-process.

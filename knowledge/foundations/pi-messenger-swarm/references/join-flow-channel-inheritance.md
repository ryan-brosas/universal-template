<!-- capsule-v2 -->
# Join flow & channel-inheritance restore — what happens on `join` for fresh, spawned, switching, and already-joined agents?

**Source:** pi-messenger-swarm MIT `main@6fe429a4b74ae276a621bb72910d7926fb6b3104`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-messenger-swarm`. **Question:** How does executeJoin reconcile register()'s session-channel default with an inherited parent channel?

## preexistingChannel save → register → conditional restore
**Path/Symbol:** `handlers/coordination/join.ts:executeJoin` (:12-161, restore block :41-48); upstream `harness/server.ts` channelHint application (:300-330); tests `tests/swarm/join-channel-inheritance.test.ts`.
**Signature:** `executeJoin(state, dirs, ctx, _deliverFn, updateStatusFn, specPath?, nameTheme?, feedRetention?, channel?, create?)`.
**Data Shape:** four outcomes: fresh join (with optional explicit channel), spawned-inherit join, switch (already registered + channel arg), no-op rejoin with peer count.

### Decisive source
```ts
// Save the channel that may have been set by resolveAgentState
// (from x-messenger-channel header for spawned agents), before
// register -> ensureStateChannels potentially overwrites it with a new session channel.
const preexistingChannel = state.currentChannel;
if (!store.register(state, dirs, ctx, nameTheme)) { ... }
if (preexistingChannel && !channel && state.currentChannel !== preexistingChannel) {
  store.joinChannel(state, dirs, preexistingChannel, { create: true });
}
```
Switch path clears per-channel chat memory:
```ts
state.chatHistory.clear(); state.channelPostHistory = [];
state.unreadCounts.clear(); state.seenSenders.clear();
```

**Flow:** unregistered+channel-arg ⇒ create/join that channel after register; unregistered+no-arg ⇒ restore preexisting hint if register clobbered it, else land on the fresh phrase session channel; registered+channel ⇒ switch with unread/history reset and 'Already in X' idempotence; registered+no-arg ⇒ ensureStateChannels re-check returning peer count. Spec attachment validates existence post-join with a warning-only miss.
**Invariant:** The save-register-restore triple exists because ensureStateChannels reads PI_MESSENGER_CHANNEL from the HARNESS env (wrong process's value) — inheritance must ride the header-resolved currentChannel, then be re-applied explicitly. An explicit --channel flag BEATS the inherited hint (`&& !channel` guard).
**Probe:** direct tests `tests/swarm/join-channel-inheritance.test.ts::preserves the pre-set channel when joining unregistered...` (:80), `::creates a new session channel when no pre-set channel (normal join without spawn)` (:114), `::respects explicit --channel flag over pre-set channel` (:151), `::does not affect already-registered agent that switches channels` (:182); `grep -c "preexistingChannel" handlers/coordination/join.ts` (=3).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-messenger-swarm", query: "executeJoin preexistingChannel joinChannel pruneFeed specWarning", limit: 5 });
```

## Verdict
Adopt save→register→conditional-restore for any default-overriding bootstrap, plus per-channel memory reset on switch; adapt wording; keep explicit-flag-beats-hint precedence.

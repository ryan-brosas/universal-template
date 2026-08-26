<!-- capsule-v2 -->
# Send-to-feed funnel & dead-agent warning — what actually happens when a message is sent?

**Source:** pi-messenger-swarm MIT `main@6fe429a4b74ae276a621bb72910d7926fb6b3104`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-messenger-swarm`. **Question:** Is `send` delivery, storage, or both — and what does the sender learn about dead recipients?

## Store-always, push-never, warn-on-terminal-spawn
**Path/Symbol:** `handlers/coordination/messaging.ts:executeSend` (:14-91), spawn-status probe (:48-63); harness-side noop `harness/server.ts:deliverMessage` (:409-415); extension-side real deliverer `extension/deliver-message.ts` (:22-66).
**Signature:** `executeSend(state, _dirs, cwd, to: string|string[]|undefined, message?, _replyTo?, channel?)`.
**Data Shape:** feed event `{type:'message', target?: to, preview: message}` on the resolved channel; warning strings keyed off SpawnedAgent.status completed/failed/stopped with ✅/❌/🛑.

### Decisive source
```ts
const spawnedAgent = findSpawnedAgentByName(cwd, sessionId, to);
if (spawnedAgent && spawnedAgent.status !== 'running') {
  spawnWarning = `\n\n⚠️ Warning: ${to} is a spawned agent that has already ${spawnedAgent.status} ${statusEmoji}. The message will be logged to the feed, but the agent process is no longer active.`;
}
// All messaging is now feed-based
logFeedEvent(cwd, state.agentName, 'message', typeof to === 'string' ? to : undefined, message, targetChannel);
```
```ts
// Pull-based message delivery: messages are written to the channel feed.
// No RPC push — this is kafka-like, not pub/sub.
const deliverMessage = (_msg: AgentMailMessage): void => {};
```

**Flow:** validate registered+message+to → resolve channel (`#x` literal vs current) → probe spawned history for terminal status → append ONE feed event regardless of recipient existence → reply text states where it posted plus optional warning. Only the OVERLAY/extension path ever pushes content into a live conversation (deliver-message with steer delivery), and even that is driven by feed readers, not by send.
**Invariant:** Delivery success is defined as durable-log-write, NOT recipient consumption — porters who add RPC push break the offline-tolerant contract the README promises ("durable even when nobody is listening"). Recipient validation is deliberately absent for registry agents (names are checked only to decorate warnings for SPAWNED agents).
**Probe:** direct tests `tests/channel-send.test.ts::send requires explicit to` class + `tests/swarm/chat-steer.test.ts::posts to feed when peers exist (no more DM delivery)` (:127), `::posts to detached channels even when no peers are present` (:99); `grep -c "kafka-like" harness/server.ts` (=1).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-messenger-swarm", query: "executeSend logFeedEvent findSpawnedAgentByName deliverMessage pull-based", limit: 6 });
```

## Verdict
Adopt store-and-warn semantics (log always; annotate terminal spawns; never fail on unknown recipients); adapt emoji/status mapping; add push channels only as readers-over-feed, never as the write path.

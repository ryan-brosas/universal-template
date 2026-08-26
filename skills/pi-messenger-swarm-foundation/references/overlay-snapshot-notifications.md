<!-- capsule-v2 -->
# Overlay snapshot & completion notifications — how does the TUI summarize swarm state on demand and detect "something finished"?

**Source:** pi-messenger-swarm MIT `main@6fe429a4b74ae276a621bb72910d7926fb6b3104`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-messenger-swarm`. **Question:** How is the background-to-chat snapshot produced and how are significant feed events surfaced once?

## generateSwarmSnapshot + computeCompletionState cache
**Path/Symbol:** `overlay/snapshot.ts:generateSwarmSnapshot` (:54+), `overlay/notifications.ts:getSignificantEventMessage` (:13+) / `computeCompletionState` (:52+); wiring `index.ts:onBackground` (:219-229) re-injecting snapshot as `swarm_snapshot` message with `triggerTurn:true`.
**Signature:** overlay background callback receives `snapshotText` from the component's done() channel.
**Data Shape:** snapshot = markdown-ish text of task buckets + recent feed activity + running workers; notification state cached per channel in `CompletionStateCache`.

### Decisive source
```ts
onBackground: (snapshotText) => {
  overlayHandle?.setHidden(true);
  pi.sendMessage({ customType: 'swarm_snapshot', content: snapshotText, display: true },
                  { triggerTurn: true });     // closing the overlay STARTS A TURN with the digest
},
```

**Flow:** user closes/hides overlay → component serializes current view (tasks by status, running spawns w/ roles, recent feed lines) → parent injects it as a displayable custom message that ALSO triggers an agent turn, so the model immediately reasons over fresh swarm state. Notification path diffs new feed events against the completion-state cache to emit at-most-once "task done" style messages.
**Invariant:** The triggerTurn flag is the seam between UI and agent loop: without it the snapshot is inert decoration; with it every overlay close consumes tokens — porters must decide deliberately. Cache keyed notification dedupe prevents replayed events from re-alerting after overlay reopen.
**Probe:** direct tests `tests/swarm/overlay-snapshot.test.ts::summarizes task buckets and recent feed activity` (:10) and `::renders the no-task empty snapshot state` (:53), `tests/swarm/litmus-statusbar.test.ts::shows summary counts when tasks exist` (:42); `grep -c "triggerTurn: true" index.ts` (=2).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-messenger-swarm", query: "generateSwarmSnapshot computeCompletionState swarm_snapshot onBackground", limit: 5 });
```

## Verdict
Adopt close-with-snapshot→turn-trigger as the UI↔agent handoff and cached-completion dedupe for event alerts; adapt rendering; omit if your host has no in-chat turn injection.

<!-- capsule-v2 -->
# connector-thread-binding-kernel — how do you map chat-platform threads to runtime sessions so mutes, identity drift, and stop-time cleanup cannot corrupt the mapping?

**Source:** Cline Apache-2.0 `main@4f836ae7d0ed29ece7ef4a2a478deb470fdd056e`; Codebase Memory `cline`. **Question:** What is the lookup, self-heal, and cleanup contract for the JSON binding store that every connector adapter shares?

## One JSON store, two binding classes; control bindings share the conversation namespace; lookup skips them; reads self-heal identity drift by rewrite; stop scrubs sessionId from three places
**Path/Symbol:** `apps/cli/src/connectors/thread-bindings.ts` (`findBindingForThread` :176-199, `readBindingForThread` :201-247, `resolveThreadControlKey` :73-75, `resolveParticipantMuteKey` :77-83, `clearBindingSessionIds` :552-577, `clearSerializedThreadSessionId` :98-121).
**Signature:** `findBindingForThread<T>(bindings: ConnectorBindingStore<T>, thread: ConnectorBindingThreadIdentity): { binding; key } | undefined`; `readBindingForThread(path, thread, errorLabel, participantKey?): ConnectorThreadBinding<T> | undefined`.
**Data Shape:** Store = `Record<string, ConnectorThreadBinding>` persisted as one JSON file. Binding carries `kind?` ("conversation" | "thread" | "thread-participant-mute"), `channelId`, `isDM`, `serializedThread` (JSON string of the platform thread), `sessionId?`, `state?`, mute timestamps. Control keys: `thread:{id}` (thread mute), `thread:{id}:participant:{key}` (participant mute).

### Decisive source
```ts
const exact = bindings[thread.id];
if (exact && !isControlBinding(exact)) {
	return { key: thread.id, binding: exact };
}
if (!thread.isDM) {
	return undefined;
}
for (const [key, binding] of Object.entries(bindings)) {
	if (isControlBinding(binding)) {
		continue;
	}
	if (binding.channelId === thread.channelId && binding.isDM === thread.isDM) {
		return { key, binding };
	}
}
```

**Flow:** exact-key hit first, skipping CONTROL bindings (mutes live in the SAME namespace as conversations, which is why every conversation lookup must skip them) ⇒ non-DM threads stop there (undefined); DM threads fall back to a scan for ANY conversation binding on the same channelId+isDM ⇒ `readBindingForThread` computes `needsRefresh` from five drift signals (key migration, stored id/channelId/isDM/participantKey mismatch) and self-heals by rewriting the binding under the target key, deleting the old key, and refreshing `serializedThread` ⇒ mutes are never tombstoned: un-mute deletes the control binding outright (`delete bindings[key]` in both `setThreadMuted` and `setParticipantMuted`) ⇒ `clearBindingSessionIds` (stop-time) scrubs sessionId from THREE places per binding: root, `state`, and inside the `serializedThread` JSON (`clearSerializedThreadSessionId` re-stringifies only when something was deleted).
**Invariant:** A control binding can never be returned as a conversation; a DM resolves to exactly one session across all its threads; identity drift is repaired on read, not flagged; stop-time cleanup leaves no sessionId anywhere in the store.
**Probe:** `thread-bindings.test.ts` (7 cases): "refreshes the serialized thread immediately when DM channel fallback rebinds a thread id", "does not rebind a different thread by participant key", "stores mute state at thread scope instead of participant scope", "clears session ids from bindings and serialized thread state". Probes: `grep -cF 'whatever shares a session' thread-bindings.ts` → 1; `grep -cF 'clearSerializedThreadSessionId' thread-bindings.ts` → 2; `grep -cF 'thread-participant-mute' thread-bindings.ts` → 4; `grep -cF 'needsRefresh' thread-bindings.ts` → 2.

## Get live surrounding code
**Retrieve (canonical call — NOT executed this session: Codebase Memory MCP transport unavailable; recorded for a connected session):**
```ts
await mcp.codebase_memory.search_graph({ project: "cline", query: "findBindingForThread readBindingForThread control binding mute thread namespace", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-class binding store with control bindings in the conversation namespace plus skip-on-lookup, DM channel fallback, read-time self-heal, delete-don't-tombstone mutes, and three-place sessionId scrub. Adapt the key formats (`thread:{id}` prefixes) and the serializedThread JSON envelope to your platform. Omit Cline's participant-label cosmetics. Coverage: source read whole at pin; 7-case direct suite read whole.

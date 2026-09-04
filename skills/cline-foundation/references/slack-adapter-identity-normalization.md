<!-- capsule-v2 -->
# Slack adapter identity normalization — how does a platform adapter repair platform quirks before the shared connector kernel sees the message?

**Source:** Cline Apache-2.0 `main@4f836ae7d0ed29ece7ef4a2a478deb470fdd056e`; Codebase Memory `cline`. **Question:** Where should Slack-specific identity repair (DM channel-type gaps, thread-ts identity, participant keys, bot self-id) live so the transport-neutral binding kernel keeps working unchanged?

## Slack identity normalization plane
**Path/Symbol:** `apps/cli/src/connectors/adapters/slack.ts:normalizeSlackMessageEventChannelType` (:136-146), `resolveSlackChannelMentionThread` (:258-289), `resolveSlackParticipant` (:152-171), `extractSlackTeamId` (:173-186), `resolveSlackBotUserId` (:247-256), `patchSlackMessageEventHandling` (:324-334).
**Signature:** `normalizeSlackMessageEventChannelType<T>(event: T): T`; `resolveSlackChannelMentionThread(thread: Thread<SlackThreadState>, message: Message): Thread<SlackThreadState>`; `resolveSlackParticipant(rawMessage: unknown, teamId?: string): { key: string; label?: string } | undefined`.
**Data Shape:** Input is the raw chat-SDK message (`message.raw` envelope: top-level / `event` / `message` records) plus the adapter's `botUserId`. Output is either the SAME event reference (no repair needed) or a shallow-copied event with `channel_type:"im"`; a rebuilt `ThreadImpl` with id `slack:{channel}:{thread_ts}`; a participant key `slack:team:{teamId}:user:{userId}`.

### Decisive source
```ts
function normalizeSlackMessageEventChannelType<T>(event: T): T {
	const record = asRecord(event);
	const channel = readString(record?.channel);
	if (!channel?.startsWith("D") || record?.channel_type === "im") {
		return event;
	}
	return { ...record, channel_type: "im" } as T;
}
```
And the thread rebuild (thread_ts preferred over the reply's own ts):
```ts
const threadTs = readString(event?.thread_ts) ?? readString(event?.ts);
...
const threadId = `slack:${channel}:${threadTs}`;
```

**Flow:** raw Slack event → `patchSlackMessageEventHandling` wraps `adapter.handleMessageEvent` so EVERY inbound event passes through the DM channel-type repair first → on mention/subscription delivery, `resolveSlackChannelMentionThread` rebuilds the thread so channel mentions bind to the ORIGINAL post's thread (`thread_ts` wins over `ts` for in-thread mentions; already-correct threads return by identity; DMs never rewritten) → `resolveSlackParticipant` + `extractSlackTeamId` derive the participant key from four user-id fallback slots (raw.user → event.user → message.user → authorizations[0].user_id) and require BOTH user and teamId (either missing ⇒ undefined) → `persistSlackThreadContext` merges teamId/participantKey/participantLabel into the thread state only when something actually changed.
**Invariant:** The shared kernel (`findBindingForThread`, `resolveThreadTurnQueueKey`) must never see an unrepaired Slack event: a DM without `channel_type:"im"` would fall out of the isDM collapse and a channel mention bound to the reply ts would fork a second session for the same Slack thread. Non-DM events must be returned by REFERENCE (no copy) so identity checks upstream stay cheap and stable.
**Probe:** `apps/cli/src/connectors/adapters/slack.test.ts` — "normalizes direct-message channels even when Slack omits im channel_type" (app_home and missing cases → `channel_type:"im"`), "leaves non-DM Slack message events unchanged" (`.toBe(channelEvent)` reference identity), "uses Slack thread_ts instead of reply ts for in-thread mentions", "keeps Slack mention threads that already target the original post" (`.toBe(original)`), "requires team context before resolving a Slack participant key" (undefined without teamId).

## Get live surrounding code
**Retrieve:** *(canonical call for a connected session — NOT executed this pass; Codebase Memory MCP transport unavailable)*
```ts
await mcp.codebase_memory.search_graph({ project: "cline", query: "normalizeSlackMessageEventChannelType resolveSlackChannelMentionThread participant key team", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the layering: platform quirks are repaired at the adapter edge, BEFORE the transport-neutral kernel, and repairs are idempotent + reference-preserving when nothing changed. Adapt the specific repairs to the target platform (Discord has no channel_type gap; Telegram topic ids play the thread-ts role). Omit the chat-SDK `ThreadImpl` rebuild mechanics if the host's thread abstraction is immutable-by-construction. Coverage caveat: normalization is fully test-pinned; `patchSlackMessageEventHandling` itself has no direct test (private adapter surface, verified by source read at :324-334).

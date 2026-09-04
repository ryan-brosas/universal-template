<!-- capsule-v2 -->
# Discord runtime context envelope — how do you make subscribed-thread noise a solvable problem for the agent instead of a filter you must get right in code?

**Source:** Cline Apache-2.0 `main@4f836ae7d0ed29ece7ef4a2a478deb470fdd056e`; Codebase Memory `cline`. **Question:** A connector subscribed to a thread receives messages that are not addressed to it — do you filter them in code, or hand the agent enough context to decide?

## XML context block + /idle self-mute protocol
**Path/Symbol:** `apps/cli/src/connectors/adapters/discord.ts:formatDiscordRuntimeText` (:248-281) + `DISCORD_SYSTEM_RULES` (:73-82) + `resolveDiscordMuteTarget` (:283-297).
**Signature:** `formatDiscordRuntimeText(text: string, participant: DiscordParticipant | undefined, options?: { ownerUserId?; isDirectMention?; isSubscribedThreadMessage? }): string`.
**Data Shape:** In: the raw message text + resolved participant + turn flags. Out: text prefixed with a `<discord_message_context>` block, or the text unchanged when no participant is known.

### Decisive source
```ts
return [
    "<discord_message_context>",
    `authorId: ${authorId}`,
    ...(participant.label ? [`authorLabel: ${participant.label}`] : []),
    `participantKey: ${participant.key}`,
    ...(options?.isDirectMention === undefined ? [] : [`isDirectMention: ${options.isDirectMention ? "true" : "false"}`]),
    ...(options?.isSubscribedThreadMessage === undefined ? [] : [`isSubscribedThreadMessage: ${...}`]),
    ...(options?.ownerUserId && options.ownerUserId === authorId ? ["isOwner: true"] : []),
    "</discord_message_context>",
    "",
    text,
].join("
");
```

**Flow:** every turn (mention, subscribed message, slash command) is wrapped with author identity and two flags — `isDirectMention` and `isSubscribedThreadMessage` — plus `isOwner` only when the author matches the configured owner id → the system rules define the protocol: when `isDirectMention` is false and the message is part of another conversation needing no action, the agent replies EXACTLY `/idle`, which the connector treats as a private no-op and never posts → `/mute@BotName [@user]` / `/unmute` instructions in the rules route into the shared mute machinery via `resolveDiscordMuteTarget`, which extracts a 15-25 digit user id from `<@id>`, `<@!id>`, or bare `@id` forms and maps it to `discord:user:{id}`.
**Invariant:** (1) Unknown flag values are OMITTED, never guessed — the agent sees only what the connector knows. (2) `/idle` is a no-op marker, not user-visible output. (3) The context block is additive: with no participant the text passes through untouched.
**Probe:** `apps/cli/src/connectors/adapters/discord.test.ts` — "adds Discord author context to runtime turns" (authorId, isOwner, isDirectMention, isSubscribedThreadMessage all asserted), "instructs Discord agents to use /idle for unrelated subscribed thread messages" (rule strings pinned), "resolves Discord mute targets from user mentions and ids" (three id forms + non-id refusal).

## Get live surrounding code
**Retrieve:** *(canonical call for a connected session — NOT executed this pass)*
```ts
await mcp.codebase_memory.get_code_snippet({ project: "cline", file: "apps/cli/src/connectors/adapters/discord.ts", symbol: "formatDiscordRuntimeText" });
```

## Verdict
Adopt the envelope pattern: pass structured turn context to the agent in a parseable block and let a reserved reply token (`/idle`) express "no action needed" — cheaper and more robust than code-side filtering of ambiguous social messages. Adapt the block name, flags, and protocol token to the host. Omit the Discord-specific mute slash-command surface. Coverage caveat: fully test-pinned.

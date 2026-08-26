<!-- capsule-v2 -->
# Delegation context protocol — how does a voice surface stay "one assistant" with the coding agent it delegates to?

**Source:** pi-better-openai MIT `main@86814e9047996abba08e4c907e23286329196fe0`; Codebase Memory `pi-better-openai`. **Question:** How are agent tool-chatter and final answers routed into the live session so the voice model narrates progress but speaks only the result?

## Delegation wiring
**Path/Symbol:** `src/live/controller.ts:#handleDelegation` (:341-356), `handleAgentMessage` (:237-252), `handleAgentSettled` (:254-266); instruction text `LIVE_INSTRUCTIONS` :18-26; index-side trigger `src/live/index.ts:registerOpenAILive` delegate closure :183-193 + `message_end`/`agent_settled` hooks :332-338.
**Signature:** `handleAgentMessage(message: unknown): void`; `handleAgentSettled(): void`; snapshot extraction `extractAssistantSnapshot` (:103-117).
**Data Shape:** Outbound: chunked context appends tagged `"commentary"` for progress vs untagged for final; final framed as literal ``"Agent Final Message":\n\n<text>``. Inbound delegation event carries `{id, content[]}`.

### Decisive source
```ts
if (snapshot.stopReason === "toolUse") {          // mid-run chatter
  for (const chunk of chunkLiveContext(snapshot.text))
    this.#queueSend(buildDelegationContextAppend(this.#activeDelegationId, chunk, "commentary"));
  return;
}
if (snapshot.text) this.#pendingAgentFinal = snapshot.text;        // hold last answer
else if (snapshot.errorMessage) this.#pendingAgentFinal = snapshot.errorMessage;

// on settle:
const context = `"Agent Final Message":\n\n${finalText}`;
for (const chunk of chunkLiveContext(context))
  this.#queueSend(buildDelegationContextAppend(delegationId, chunk));
this.#activeDelegationId = undefined;             // closes the working phase
```

**Flow:** model emits `delegation.created` → join text content into request → set active id + phase "working" → host `delegate()` triggers a turn (steer delivery) → each `message_end` during work streams commentary chunks → `agent_settled` sends the held final (or a no-final fallback string) → id cleared.
**Invariant:** Commentary is marked `commentary` and per instructions MUST NOT be recited; only the settled final is presentable ("present its useful result naturally as your own") — the one-assistant illusion is enforced jointly by channel tagging and prompt doctrine; messages arriving with NO active delegation are ignored (:238).
**Probe:** `tests/live-controller.test.ts` (:85/:90 handleAgentMessage paths, :95 handleAgentSettled) and `tests/live-registration.test.ts` (:175 message_end→agent_settled ordering).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-better-openai", query: "handleAgentSettled pendingAgentFinal delegation.created", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-lane routing (tagged live commentary vs held-and-framed final) plus the settle-closes-delegation lifecycle. Adapt framing strings and the delegate hook to your host. Omit the Codex-specific instruction prose unless building the same persona.

<!-- capsule-v2 -->
# Interview turn injection — how does a UI command hand control to the agent as if the user had typed a message, without racing an in-flight turn?

**Source:** pi-hermes-memory (MIT, `main@71beae8a53be2cdc4901744cf85bd65a1b3030e6`); Codebase Memory `pi-hermes-memory`. **Question:** What is the safe sequence for a slash command to trigger an agent turn driven by extension-authored prompt text?

## Wait for idle, then send the prompt as a user message — always
**Path/Symbol:** `src/handlers/interview.ts:registerInterviewCommand` (:13–37); prompt constant `INTERVIEW_PROMPT` imported from `src/constants.ts` (:11).
**Signature:** `registerInterviewCommand(pi: ExtensionAPI, store: MemoryStore): void`; handler `async (_args, ctx) => void` using `ctx.ui.notify`, `ctx.waitForIdle`, `pi.sendUserMessage`.
**Data Shape:** reads `store.getUserEntries(): string[]`; sends one fixed string (`INTERVIEW_PROMPT`, a constants-owned prompt pack); optional pre-notification is display-only.

### Decisive source
```ts
// src/handlers/interview.ts:32-34
// Send the interview prompt as a user message to trigger the agent turn
await ctx.waitForIdle();
pi.sendUserMessage(INTERVIEW_PROMPT);
```

**Flow:** (1) read existing USER.md profile entries; (2) if any exist, notify first — count with singular/plural grammar ("1 profile entry" vs "N profile entries"), 80-char-truncated previews, and an "add to or update these" framing; (3) `await ctx.waitForIdle()` so the injected message cannot interleave with an in-flight agent turn or pending tool work; (4) `pi.sendUserMessage(INTERVIEW_PROMPT)` enqueues the prompt as a genuine user message, giving the model the full normal turn context rather than a side-channel.
**Invariant:** the interview prompt is sent UNCONDITIONALLY — existing entries change the preamble notification, never the send (re-running the interview updates/adds profile facts instead of being suppressed); the idle wait must precede the send or two agents can answer overlapping prompts.
**Probe:** `tests/handlers/interview.test.ts` — "sends interview prompt as user message when USER.md is empty", "still sends interview prompt even when entries exist", "uses correct message count grammar (1 entry)", plus registration/description checks. Executed GREEN pre-write: 6 passed / 0 failed (`npx tsx --test`). Coverage: `src/handlers/interview.ts` + test path `no_recorded_issue` @ gen 2026-08-24T14:05:19Z.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-hermes-memory", query: "registerInterviewCommand waitForIdle sendUserMessage INTERVIEW_PROMPT", limit: 10, fields: ["signature", "lines"] });
```

## Verdict
Adopt the two-step handoff (`waitForIdle` → `sendUserMessage`) for ANY command that needs an agent turn, not just onboarding. Adapt the API names to your host's queue/steer surface. Omit the pre-notification grammar detail unless your host surfaces command output to users. Caveat: `INTERVIEW_PROMPT` content lives in constants.ts prompt packs (standing omission — content, not mechanism).

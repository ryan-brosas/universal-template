<!-- capsule-v2 -->
# DeepAgents instructions-once — when reattaching to a live agent process, how do you know whether session instructions must be resent?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f2243035491e9de5a2e00ebf9eb17`; Codebase Memory `ai`. **Question:** Session instructions are baked into a long-lived agent process at build time — after detach/reattach (or respawn), how does the host decide whether the start frame must carry them again?

## Attached-seeded once flag
**Path/Symbol:** `packages/harness-deepagents/src/deepagents-harness.ts` — `attached` parameter doc (:616–619), `instructionsApplied` seed (:627), `applyInstructions` in doPromptTurn (:771–778), attach/replay no-start comment in doContinueTurn (:810).
**Signature:** `createSession({..., isResume, attached, ...}): HarnessV1Session`; start frame field `instructions?: string` included only when `!instructionsApplied && promptOpts.instructions`.
**Data Shape:** `attached: boolean` — true ONLY when attaching to a live bridge that already built the agent with its instructions; `instructionsApplied: boolean` seeded from it; fresh spawn (including respawn-on-attach-failure and stop-resume) passes `attached: false`.

### Decisive source
```ts
// deepagents-harness.ts:616–627 — the flag's contract in its own words
// True only when attaching to a live bridge that already built the agent with
// its instructions. A fresh spawn (incl. a respawn on attach failure or a
// stop-resume) starts a new bridge that must receive the instructions again.
attached: boolean;
// ...
let instructionsApplied = attached;
// :771–778 — the single injection point
const applyInstructions = !instructionsApplied && !!promptOpts.instructions;
instructionsApplied = true;
channel.send({
  type: 'start',
  prompt: extractUserText(promptOpts.prompt),
  ...(applyInstructions ? { instructions: promptOpts.instructions } : {}),
  /* tools, responseFormat, model, thinking, effort, skillsPaths, ... */
});
```

**Flow:** doStart first tries live attach against persisted bridge coordinates → on success createSession receives `attached: true`, so `instructionsApplied` seeds TRUE and the next start frame omits instructions → on attach failure the host respawns a fresh bridge (`attached: false`) and the first doPromptTurn includes `instructions` in the start frame and latches applied → doContinueTurn sends NO start frame at all for attach/replay (a start would clear the replay log), so there is exactly one injection point per bridge process lifetime.
**Invariant:** instructions ride the start frame AT MOST ONCE per bridge process lifetime — an attached bridge must not receive them again (double system-prompt injection into an already-built agent), and every fresh spawn must receive them; the latch flips unconditionally on the first prompt even when no instructions were provided, so a later prompt cannot retroactively inject stale ones.
**Probe:** NO test pins `instructionsApplied` directly (coverage caveat — deterministic read only); the attach/respawn boundary it depends on is pinned by `deepagents-harness.test.ts:345–394` ("reuses a caller-minted token and passes endpoint headers when attaching" — mintBridgeToken called exactly once across detach/reattach) and the suspended-close contract :396–408.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "instructionsApplied attached deepagents start frame instructions", limit: 10 });
```

## Verdict
Adopt the attached-seeded once flag for any dialect where session config is baked into a long-lived process at build time; adapt the flag name and the frame field; omit for dialects that resend instructions on EVERY start frame when provided (opencode and claude-code both spread `promptOpts.instructions` into each start message — idempotent by design because their runtimes treat it as per-turn context). Caveat: read-only evidence, no direct test.

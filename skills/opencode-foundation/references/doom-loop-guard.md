<!-- capsule-v2 -->
# Doom-loop guard — how do you stop an agent from re-running the same failing tool call forever?

**Source:** opencode (Slate-licensed monorepo) @ `dev@0352100`; Codebase Memory `opencode`. **Question:** What exactly counts as a "repeat" tool call, and what happens when the threshold trips — does the turn fail or ask?

## The repeat detector
**Path/Symbol:** `packages/opencode/src/session/processor.ts` `handleEvent` `"tool-call"` arm (:331-381); `DOOM_LOOP_THRESHOLD = 3` (:29).
**Signature:** guard runs on EVERY `tool-call` event after `ensureToolCall`/`updateToolCall`; no separate function.
**Data Shape:** compares against the last `DOOM_LOOP_THRESHOLD` persisted parts of the assistant message (`parts.slice(-3)`), each part needing: type `tool`, same `tool` name, status NOT `pending`, and `JSON.stringify(part.state.input) === JSON.stringify(input)`.

### Decisive source
```ts
// processor.ts:356-369 — canonical-JSON input equality over the trailing window;
// pending parts don't count (a call that never started is not a "run")
const recentParts = parts.slice(-DOOM_LOOP_THRESHOLD)
if (
  recentParts.length !== DOOM_LOOP_THRESHOLD ||
  !recentParts.every(
    (part) =>
      part.type === "tool" &&
      part.tool === value.name &&
      part.state.status !== "pending" &&
      JSON.stringify(part.state.input) === JSON.stringify(input),
  )
) {
  return
}
const agent = yield* agents.get(ctx.assistantMessage.agent)
yield* permission.ask({
  permission: "doom_loop",
  patterns: [value.name],
  ...
  always: [value.name],
  ruleset: agent.permission,
})
```

**Flow:** three identical consecutive executions of the SAME tool with byte-equal inputs ⇒ raise a `doom_loop` permission ASK (not an error, not a break). The ask carries `always: [value.name]` so an "always allow" answer whitelists that tool for the rest of the session. If the user DENIES, normal permission-rejection handling takes over (`failToolCall` marks RejectedError and sets `ctx.blocked = ctx.shouldBreak` :200-202), which turns the turn result into `"stop"` via the standard path. A summary-generating message refuses tool calls outright BEFORE this guard (`Tool call not allowed while generating summary` :316-318/:332-334).
**Invariant:** The comparison is over PERSISTED parts read back from the message store, not an in-memory history — restarts and replays see the same repeats. Byte-equality via JSON.stringify means key ORDER matters; two calls that differ only in key order are NOT doom-loop repeats. Threshold counts the assistant's own most recent tool parts regardless of interleaved text/reasoning parts.
**Probe:** direct pins (execute from repo root):
```bash
grep -n 'permission: "doom_loop"' packages/opencode/src/session/processor.ts
grep -c 'JSON.stringify(part.state.input) === JSON.stringify(input)' packages/opencode/src/session/processor.ts
```
expect one hit at :372 and count 1 at :365.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_code({ project: "opencode", pattern: "DOOM_LOOP_THRESHOLD", limit: 5 });
// rank-1 = packages.opencode.src.session.processor.DOOM_LOOP_THRESHOLD Variable processor.ts :29,
// plus processor.layer :81-697 match lines 356/359 — the exact guard body
// (plain BM25 "doom_loop"/multi-word queries return zero or permission-UI noise on this graph)
```

## Verdict
Adopt the trailing-window canonical-JSON repeat detector and the ask-don't-fail posture (permission ask with always-whitelist instead of hard abort); adapt the permission schema names; omit opencode's agent-ruleset plumbing if the host has no per-agent permissions.

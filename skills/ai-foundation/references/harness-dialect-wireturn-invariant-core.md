<!-- capsule-v2 -->
# Dialect wireTurn invariant core — what is the per-turn pump contract every runtime dialect replicates, and which knobs may vary?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f2243035491e9de5a2e00ebf9eb17`; Codebase Memory `ai`. **Question:** When adding a new runtime dialect adapter, which turn-pump plumbing must be replicated exactly, and which knobs are the only legitimate points of variation between dialects?

## The replicated pump core (four dialects, one shape)
**Path/Symbol:** `packages/harness-opencode/src/opencode-harness.ts` — `wireTurn` (:804–946); `packages/harness-codex/src/codex-harness.ts` — `wireTurn` (:736–881); `packages/harness-claude-code/src/claude-code-harness.ts` — `wireTurn` (:1517–1655); `packages/harness-deepagents/src/deepagents-harness.ts` — `wireTurn` (:629–742).
**Signature:** `wireTurn({emit, abortSignal?}): HarnessV1PromptControl` where control = `{submitToolResult(input), submitToolApproval(input), done: Promise<void>}` plus `submitUserMessage(text)` only when the bridge advertised acknowledged user messages.
**Data Shape:** per-turn locals — `done` promise with captured `pendingResolve`/`pendingReject`; `unsubs: Array<() => void>`; `isSettled` latch; a per-dialect `eventTypes` const array; optional `userMessageSubmitter`. All four share the base vocabulary `stream-start, text-start/delta/end, reasoning-start/delta/end, tool-call, tool-approval-request, tool-result, finish-step, raw`; opencode adds `file-change, compaction`, codex and deepagents add `file-change`, claude-code adds neither.

### Decisive source
```ts
// deepagents-harness.ts:662–703 — the most compact copy of the shared core
let isSettled = false;
const settleSuccess = () => {
  if (isSettled) return;
  isSettled = true;
  for (const u of unsubs) u();
  pendingResolve!();
};
const settleError = (err: unknown) => {
  if (isSettled) return;
  isSettled = true;
  for (const u of unsubs) u();
  pendingReject!(err);
};
for (const type of eventTypes) {
  unsubs.push(channel.on(type, msg => forward(msg)));
}
unsubs.push(channel.on('finish', msg => { forward(msg); settleSuccess(); }));
unsubs.push(channel.on('error', msg => { forward(msg); settleError(msg.error); }));
// A `'suspended'` close is a graceful slice-boundary freeze (suspend/detach keep
// the bridge alive for continuation); end the turn cleanly. Any other close is
// an unexpected bridge failure.
const onClose = (_code: number, reason: string) => {
  if (isSettled) return;
  if (reason === 'suspended') { settleSuccess(); return; }
  settleError(new Error('deepagents bridge closed before the turn finished.'));
};
channel.onClose(onClose);
const onAbort = () => {
  if (isSettled) return;
  try { channel.send({ type: 'abort' }); } catch {}
  settleError(
    turnOpts.abortSignal?.reason ?? new DOMException('Aborted', 'AbortError'),
  );
};
```

The one non-uniform detail in the core is codex's deferred start frame — the only dialect that does not send `start` synchronously:
```ts
// codex-harness.ts:864–879 — defer the start frame one event-loop turn
sendStart: send => {
  /*
   * Codex can complete short turns without using tools. Deferring the
   * start frame gives the harness runner one event-loop turn to finish
   * wiring the prompt control and stream output before Codex can settle.
   */
  const timer = setTimeout(() => {
    if (isSettled) return;
    try { send(); } catch (err) { settleError(err); }
  }, 0);
  timer.unref?.();
},
```

**Flow:** doPromptTurn/doContinueTurn call wireTurn FIRST (all listeners subscribed) and only afterwards send the `start` frame — or send nothing at all for attach/replay, because a start frame would clear the bridge's replay log — and send a non-empty `'Continue.'` nudge only for lossy rerun → each event type in the dialect list forwards verbatim through a try/catch-wrapped emit → `finish` forwards then settles success; `error` forwards then settles failure → any close other than `'suspended'` mid-turn settles failure with the dialect-named "bridge closed before the turn finished" → caller abort sends best-effort `{type:'abort'}` and settles with `signal.reason` or a synthesized AbortError → settle runs every unsub (and closes the userMessageSubmitter where present) so late channel events cannot re-enter consumer code.
**Invariant:** the done promise settles EXACTLY ONCE no matter how many terminal paths race (finish vs error vs close vs abort); a `'suspended'` close is ALWAYS success (slice boundary — the turn keeps running in the bridge and its tail replays to the next process) while every other close is ALWAYS failure; a throwing consumer cannot kill the pump; the listener set is torn down at settle, never before.
**Probe:** direct tests `packages/harness-deepagents/src/deepagents-harness.test.ts:396–408` ("resolves the turn when the channel closes with reason 'suspended'" / "rejects the turn when the channel closes for any other reason" — the only dialect package with direct close-reason cases); the same contract is pinned indirectly through opencode/codex/claude-code adapter cases. Caveat: NO dialect package has a dedicated wireTurn unit file — behavior is pinned through adapter-level integration cases.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "wireTurn settleSuccess settleError suspended submitToolResult eventTypes", limit: 10 });
```

## Verdict
Adopt the pump core as a checklist for any new dialect (settle-once latch, suspended=success, forward-swallow, abort frame + signal.reason, unsub-on-settle, wire-then-send ordering); adapt the eventTypes list, the control surface, and start-frame timing to the runtime; omit ACP's open-block synthesis — dialect bridges already emit well-formed blocks, unlike the pass-22 ACP pump which manufactures them. Caveat: pinned through adapter tests, not a dedicated wireTurn suite.

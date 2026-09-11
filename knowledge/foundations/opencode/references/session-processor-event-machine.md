<!-- capsule-v2 -->
# Session processor event machine — how do LLM stream events become persisted session parts, and what does a turn return?

**Source:** opencode (Slate-licensed monorepo) @ `dev@0352100` (pass-5 refresh from `4643e65a`, 116 upstream commits); Codebase Memory `opencode`. **Question:** How does one component translate the raw LLM event stream into session parts while deciding compact/stop/continue, and which cleanup must run even when the stream dies mid-tool?

## The per-turn state machine
**Path/Symbol:** `packages/opencode/src/session/processor.ts` (`ProcessorContext` :67-75, `handleEvent` :278-537, `process` :627-683, `cleanup` :539-597).
**Signature:** `create({assistantMessage, sessionID, model}) → Handle{message, updateToolCall, completeToolCall, process(streamInput) → Effect<Result>}` where `Result = "compact" | "stop" | "continue"`.
**Data Shape:** `ctx.toolcalls: Record<callID, {partID, messageID, sessionID, done: Deferred<void>}>`; `reasoningMap: Record<id, ReasoningPart>`; scalar flags `shouldBreak/blocked/needsCompaction`; `snapshot: string | undefined` (pre-turn git snapshot hash); `currentText` is the single in-flight TextPart.

### Decisive source
```ts
// processor.ts:99-102 — snapshot captured BEFORE the stream: the AI SDK may run tools
// internally before emitting start-step, so capturing inside the handler is too late.
const initialSnapshot = yield* snapshot.track()
// processor.ts:642-646 — the whole stream loop is three combinators:
yield* stream.pipe(
  Stream.tap((event) => handleEvent(event)),
  Stream.takeUntil(() => ctx.needsCompaction),   // overflow ⇒ stop draining, keep part state
  Stream.runDrain,
)
```

**Flow:** `process()` resets `needsCompaction`, reads `shouldBreak = config.experimental?.continue_loop_on_deny !== true` (:633), sets status busy, drains the LLM stream through `handleEvent`. Event arms: reasoning-start/delta/end maintain `reasoningMap` (orphan deltas silently dropped :295-296); tool-input-* idempotently `ensureToolCall` (creates pending part + Deferred); tool-call marks running + feeds the DOOM-LOOP guard; tool-result normalizes attachments (failed image resizes are dropped with an `[N images omitted…]` suffix appended to output :402-409); step-finish writes usage/cost, forks `summary.summarize` into the request scope with `Effect.ignore` (:471-476), computes `isOverflow → needsCompaction`; text-end runs the `experimental.text.complete` plugin trigger and REPLACES the text (:516-524). After drain: `"compact"` if needsCompaction, else `"stop"` if blocked or assistantMessage.error, else `"continue"` (:679-681). Error path: inner gen wrapped by `Effect.onInterrupt` (abort ⇒ halt(AbortError) unless an error already recorded), retry via `SessionRetry.policy`, then `Effect.catch(halt)`, and `Effect.ensuring(cleanup())` — cleanup ALWAYS runs (:648-676).
**Invariant:** `halt()` classifies ContextOverflowError specially: if `compaction.auto === false` and not a summary message, record error + idle and RETURN normally (:607-614); otherwise set needsCompaction and let the outer loop decide (:615-617). Interrupt-only causes must NOT reach `halt` as failures (`catchCauseIf(!hasInterruptsOnly)` :656-659) or aborts double-report. `finishReasoning` uses a deliberate SELF-ASSIGN (`text = text`) as reactivity trigger (:209-210) — removing the "no-op" breaks UI updates.
**Probe:** direct pins (execute from repo root):
```bash
grep -n 'DOOM_LOOP_THRESHOLD = 3' packages/opencode/src/session/processor.ts
grep -n 'takeUntil' packages/opencode/src/session/processor.ts
grep -n '250 millis' packages/opencode/src/session/processor.ts
```
expect exactly one hit each (:29, :644, :573).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", qn_pattern: "packages.opencode.src.session.processor", limit: 10, detail: "ids" });
// resolves the processor module plane: DOOM_LOOP_THRESHOLD :29, ProcessorContext, Handle, Service…
// (BM25 multi-symbol queries on this file return TUI noise; the qn_pattern sweep is the reliable primitive.
//  For line-exact bodies: search_code pattern:"settleToolCall" → processor.layer :81-697 matches :123/:183/:203)
```

## Verdict
Adopt the three-result turn contract (compact/stop/continue), pre-stream snapshot capture, ensure/settle tool-call lifecycle over Deferreds, and ensuring-cleanup semantics; adapt the Effect/Stream plumbing to host runtime; omit opencode-specific status/event bridge names.

<!-- capsule-v2 -->
# Mid-run signal gate — signal-triggered mid-run steering with the confidence bar and intervention-before-send ordering

**Source:** ext-pi-supervisor MIT `master@92c0d6df986dfd138f941001e3fcc57a3ee07247`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-supervisor`. **Question:** When is the supervisor allowed to interrupt an agent that is actively working, and what extra conditions apply versus the settled path?

## Reactive signals replace a blind turn counter
**Path/Symbol:** `src/index.ts:201-226` (`pi.on('turn_end')` handler); detector `src/state/mid-run-signals.ts:31-103`.
**Signature:** `detectMidRunSignals(messages: Message[]): MidRunSignal | null` where `MidRunSignal = { type: 'tool_error' | 'file_read_loop', detail?: string }`.
**Data Shape:** Scans only the last `SIGNAL_WINDOW = 30` messages (`mid-run-signals.ts:18`), normalizes+filters to blocks, returns the FIRST signal by severity (tool_error checked before file_read_loop).

### Decisive source
```ts
pi.on('turn_end', async (_event, ctx) => {
    currentCtx = ctx;
    if (!state.isActive()) return;
    const messages = extractMessages(ctx);
    const signal = detectMidRunSignals(messages);
    if (!signal) return;
    let decision;
    try {
      decision = await analyze(ctx, state.getState()!, false /* agent still working */);
    } catch { return; }
    if (decision.action === 'steer' && decision.message && decision.confidence >= 0.85) {
      state.addIntervention({ ... });
      updateUI(...{ type: 'steering', message: decision.message });
      pi.sendUserMessage(decision.message, { deliverAs: 'steer' });
    }
```
Threshold constants (`src/state/mid-run-signals.ts`): `CONSECUTIVE_ERROR_THRESHOLD = 5` (:42) counting error results separated by their tool_call within the last 10 blocks; `FILE_READ_LOOP_THRESHOLD = 5` (:21) keyed by path+offset/limit so paginated reads never loop-fire (:69-78); any Edit/Write/MultiEdit of that file deletes its read counter (:86-88).

**Flow:** every LLM sub-turn → cheap deterministic signal scan → no signal ⇒ zero cost → signal ⇒ full analyze in WORKING mode → steer ONLY at confidence ≥ 0.85 → record intervention → UI → send as `'steer'` delivery.
**Invariant:** mid-run steering requires BOTH a mechanical trigger AND higher confidence than the settled path needs (0.85 vs any steer message); analysis failure mid-run silently continues (never nudges — the agent is still moving). The signal window and per-file keying must stay aligned: same file different offsets ≠ loop.
**Probe:** `grep -cn ">= CONSECUTIVE_ERROR_THRESHOLD\|>= FILE_READ_LOOP_THRESHOLD" src/state/mid-run-signals.ts` → 2; direct test pins: `tests/state.test.ts:330` "detects five consecutive tool errors", `tests/state.test.ts:395` "resets read loop counter when file is edited", `tests/state.test.ts:414` "does not trigger file read loop when reading same file with different offsets".

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-supervisor", query: "detectMidRunSignals file_read_loop consecutive tool errors", limit: 10 });
```

## Verdict
Adopt the two-arm design: free deterministic watchers decide WHEN to look, the expensive model decides WHAT to say. Adapt tool-name sets (FILE_MUTATION_TOOLS / FILE_READ_TOOLS carry both TitleCase and snake_case names) to your host's tool vocabulary. Omit the specific 0.85 constant only with a replacement confidence bar — mid-run interruptions without one will fire on weak evidence.

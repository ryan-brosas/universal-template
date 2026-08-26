<!-- capsule-v2 -->
# Context-transform integration spine — how does an extension rewrite the LLM-bound message array every turn without corrupting session state?

**Source:** billion-context-pi (MIT) `master@1c87eb5051e0e97bb6ba606dc1c57ec2510f1b41`; Codebase Memory project `mnt-hdd-utopia-inspo-coding-agents-billion-context-pi`. **Question:** What is the correct shape of the per-LLM-call context transform (locking, token truth, config layering, state save, rebuild, nudge injection) that a porter must preserve?

## The context-event pipeline: lock → load → re-center/reserve → transform → save → rebuild → inject
**Path/Symbol:** `src/index.ts`: `wireContextTransform` (`pi.on("context")`, :131-377).
**Signature:** `(event, ctx) => Promise<{ messages: AgentMessage[] }>` — must ALWAYS return the transformed array.
**Data Shape:** input = event.messages (exact messages about to be sent, incl. not-yet-persisted tail) + persisted session entries; internal = per-turn layered Config + acp-kernel `processTurn({messages, state, config, tokenCount})`; output = rebuilt AgentMessage[] plus optional appended nudge / compress-retry user-messages.

### Decisive source
```ts
// index.ts:131-234 (pass-4 pin) — mutex + config layering + sent-view tokenCount:
const release = await runtime.acquireLock(sid);
try {
  await runtime.reloadConfig(ctx.cwd);            // live acp.json edits apply mid-session
  runtime.setCountModel(modelId);                 // density calibration is per-model
  const { state, coreMessages, entries } = await runtime.stateFor(ctx, event.messages);
  const ov = runtime.overflowFor(sid);
  // learned overflow window SHRINKS the resolved limit (spread, never mutate):
  if (learnedWindow && learnedWindow > 0 && learnedWindow < config.modelContextLimit)
    config = { ...config, modelContextLimit: learnedWindow };
  // output headroom reservation (non-Anthropic only):
  if (shouldReserveOutputHeadroom(api)) config = { ...config, modelContextLimit: reservedWindow };
  ...
  let tokenCount = calibrateTokens(sentTokens, runtime.density.densityFor(modelId));
  if (ov.armed && config.modelContextLimit > 0) { ov.armed = false;
    const floor = Math.floor(config.modelContextLimit * 0.95);
    if (floor > tokenCount) tokenCount = floor; }   // armed self-heal emergency
  const turn = runtime.core.processTurn({ messages: coreMessages, state, config, tokenCount });
  await runtime.save(turn.state, ctx);
```
**Flow:** acquire a per-session async mutex → live-reload config (JSON-keyed no-op when unchanged; re-derives from FACTORY config "so a key REMOVED from acp.json actually reverts") → load state and merge any not-yet-persisted tail messages → layer the window three times (learned overflow window shrink-only; output-headroom reservation except anthropic-messages; both via spread into NEW objects) → compute the CALIBRATED SENT-VIEW tokenCount (see sent-view-arbitration capsule; raw estimate feeds density.update AFTER save so calibration never chases itself) → run the kernel turn → SAVE returned state unconditionally ("Always return the transformed array… there is no meaningful 'no change' case" :356-357) → rebuild AgentMessage[] via id-keyed maps (`collectOriginals` also projects `custom_message` entries as role:"user" because pi's convertToLlm does and a literal "custom" role would be dropped) → append compress-retry then nudge synthetic user messages → fire-and-forget update check on EVERY context event too ("resuming a long-running session never re-fires session_start", :359-362; awaited only when headless). Errors log-and-RETHROW inside try; `finally release()` guarantees mutex unlock.
**Invariant:** (1) tokenCount is decision-scale only — it must NOT feed density.update (raw basis rule). (2) The armed-emergency floor consumes the flag exactly once (:204). (3) postCompression detection compares LOADED active blocks vs previous round's snapshot (`noteActiveBlocks`) — never a single processTurn in/out diff, because compress runs out-of-band between events (:211-218). (4) Nudge dedup keys on last-user-entry with emergency bypass AND retry-cap override (nudge-injection-channels capsule). (5) Whole handler wrapped lock→try→finally-release; a throw without unlock deadlocks the session forever.
**Probe:** `cd /mnt/hdd/utopia/inspo/coding-agents/billion-context-pi && npx tsx --test tests/integration.test.ts tests/sent-view-arbitration.test.ts` — GREEN at pass-4 pin (ref-tagging parity, omp tail-merge stability, sent-view scale pins).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-coding-agents-billion-context-pi", query: "wireContextTransform processTurn reloadConfig calibrateTokens", limit: 10 });
```

## Verdict
Adopt the whole spine: per-session mutex around read-transform-save, live config reload with factory-base re-derivation, layered window adjustments (spread-not-mutate), calibrated sent-view token truth, unconditional array return, last-user-turn nudge key with bypass+cap. Adapt host event names (`context`, `session_before_compact`) to your surface. Omit pi's built-in compaction entirely — this extension CANCELS it (`session_before_compact => ({cancel:true})`) because ACP owns compression; two writers on one context is a corruption race.

<!-- capsule-v2 -->
# Nudge injection channels — how does a compression prompt reach the model every turn it matters, exactly once per turn, without permanently polluting context?

**Source:** billion-context-pi (MIT) `master@1c87eb5051e0e97bb6ba606dc1c57ec2510f1b41`; Codebase Memory project `mnt-hdd-utopia-inspo-coding-agents-billion-context-pi`. **Question:** How must the nudge be appended to the rebuilt message array so repeated host context-events cannot stack duplicate copies, and why is the emergency tier exempt?

## CONTEXT channel append + debug-only TERMINAL echo + emergency dedup bypass + retry-cap suppression
**Path/Symbol:** `src/index.ts`: nudge block (:296-339), `nudgeMessage` builder (:565-590); keys via `lastUserMessageId` (`src/tokens.ts` :33-39); runtime Set (`markNudgeShown`/`nudgeShownFor`, runtime.ts :413 return object); cap gate `compressRetryCappedFor` (runtime.ts :318-320).
**Signature:** `rebuilt.push(nudgeMessage(turn.nudge, activeBlocks, prompts))`; gate = `retryCapped || (!emergency && runtime.nudgeShownFor(turnKey))`; turnKey = `lastUserMessageId(entries) ?? sid`.
**Data Shape:** synthetic user-role AgentMessage: rendered nudge text + block census line ("Compressed blocks: N active (T1:a T2:b) — X summary, Y original compressed. Blocks: <first 10 ids> (+Z more).") + a worked example built from the LARGEST compressible range AFTER kernel-side `viableRanges` filtering (:314 — "a tiny fragmented range in the list makes batched attempts fail atomically; kernel validates the whole batch").
### Decisive source
```ts
// src/index.ts:305-322 (pass-4 pin) — two escape hatches on one gate:
// Emergency nudges (usage >= 80%) bypass the per-turn dedup so the
// overflow warning always reaches the model. Other nudges inject at most
// once per turn: pi fires the context event multiple times per assistant
// reply (streaming/tool loop), and without this gate the same nudge
// would be appended on every event.
const emergency = turn.nudge.breakdown?.emergencyOverride === 1;
// Retry-cap circuit breaker (issue #6): emergency nudges re-inject on
// every LLM call, so a model answering each one with a failed/no-op
// compress call loops forever ... Once this turn burned
// MAX_COMPRESS_ATTEMPTS attempts, stop re-injecting the nudge — the
// kernel's emergency truncation still shrinks context mechanically.
const retryCapped = runtime.compressRetryCappedFor(turnKey);
const alreadyShown = retryCapped || (!emergency && runtime.nudgeShownFor(turnKey));
```
**Flow:** kernel returns a nudge decision → filter its compressibleRanges through `viableRanges` → compute turnKey from the LAST user entry (falls back to session id pre-first-user-message) → suppress when the retry cap burned this turn OR already shown this turn UNLESS emergencyOverride → append synthetic user message carrying rendered text + block census + worked example from the top-token range → debug mode additionally echoes the exact injected text via ui.notify (channel 2 — "The model never sees terminal output"). Because the next context event rebuilds the array from scratch, the append never persists.
**Invariant:** (1) the nudge is a PER-REBUILD append, never written into session state — persistence would poison every future turn; (2) dedup keys on the last USER message (turn granularity), not wall-clock or call count, because hosts fire multiple context events per assistant reply; (3) emergency (≥80%) nudges deliberately skip dedup — an overflow warning suppressed as "already shown" can strand the session over limit; (4) NEW: the same re-inject-every-call property that makes the bypass necessary also makes emergency+failed-compress a LOOP — the retry-cap breaker (see compress-retry-breaker capsule) must be able to suppress even emergency nudges, while mechanical kernel truncation stays outside the gate as the safety floor.
**Probe:** `cd /mnt/hdd/utopia/inspo/coding-agents/billion-context-pi && npx tsx --test tests/compress-retry.test.ts tests/tokens.test.ts` — GREEN at pin (cap reachability incl. emergency loop case; turnKey derivation). Line anchors grep-verified at pass-4 pin: :296/:305-313/:314/:321-322.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-coding-agents-billion-context-pi", query: "nudgeMessage renderNudgeText markNudgeShown compressRetryCappedFor", limit: 10 });
```

## Verdict
Adopt the append-per-rebuild pattern with last-user-message turn keys, viableRanges pre-filtering, and BOTH gates (emergency dedup bypass AND retry-cap override). Adapt the rendered voice/example grammar to your tool surface. Omit the terminal echo outside debug builds.

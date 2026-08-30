<!-- capsule-v2 -->
# Ineffective-steering pattern detection — when do repeated steers mean the STRATEGY is failing?

**Source:** pi-supervisor MIT `master@92c0d6d`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-supervisor`. **Question:** How does the supervisor know its own steering stopped working, using only intervention records — no turn counting?

## detectIneffectivePattern (`src/state/patterns.ts`)
**Path/Symbol:** `src/state/patterns.ts:detectIneffectivePattern` (:22-52), `areMessagesSimilar` (:54-82), `STAGNATION_SECS=60` (:15).
**Signature:** `detectIneffectivePattern(state: Pick<SupervisorState,'interventions'|'startedAt'>): IneffectivePattern` where `IneffectivePattern = {detected, similarCount, secondsSinceLastSteer}`.
**Data Shape:** Reads ONLY the last 3 interventions (`slice(-3)`); `lastSteerTs = last intervention timestamp ?? state.startedAt`.

### Decisive source
```ts
const stagnating = secondsSinceLastSteer >= STAGNATION_SECS;   // time-based arm
const recent = state.interventions.slice(-3);
if (recent.length < 2) return { detected: stagnating, similarCount: recent.length, ... };
// similarity run-length over consecutive pairs:
for (let i = 1; i < messages.length; i++)
  if (areMessagesSimilar(messages[i-1], messages[i])) similarCount++;
const detected = similarCount >= 2 || stagnating;

function areMessagesSimilar(a, b) {
  if (normA === normB) return true;
  const commonDirectives = aDirectives.filter(w => bDirectives.includes(w));
  if (commonDirectives.length >= 2) return true;              // ≥2 shared directive words
  const lenRatio = Math.min(lenA,lenB) / Math.max(lenA,lenB);
  if (lenRatio > 0.7 && commonDirectives.length >= 1) return true; // near-equal + 1 shared
  return false;
}
```

**Flow:** `agent_settled` → `state.detectIneffectivePattern()` → if `detected && reframeTier < 4` escalate tier (escalation itself persists) → tier guidance injected into the next supervisor prompt. Directive vocabulary: focus/implement/add/fix/create/build/need/should/must; comparison happens on punctuation-stripped lowercase text.
**Invariant:** (1) Two arms are OR-ed — either repetition OR silence flags ineffectiveness; with <2 interventions ONLY stagnation can fire. (2) Stagnation is measured from the last steer's OWN timestamp, so a steer issued long ago keeps counting even while the agent works. (3) Similarity is deliberately crude (shared directive words + length ratio), because exact repeats are rare — paraphrases must count. (4) Tier caps at 4 and resets to 0 on done/stop/new supervision.
**Probe:** `tests/state.test.ts` — `returns no pattern with less than 2 interventions` (:103), `detects similar messages` (:112), `detects stagnation (no steer in a while)` (:134), `detects dissimilar messages as different` (:150).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-supervisor", query: "detectIneffectivePattern STAGNATION_SECS directiveWords", limit: 8 });
```

## Verdict
Adopt the two-arm detection + similarity heuristic as-is for any steering loop that logs interventions with timestamps. Adapt the directive-word list to your domain language. Omit pi-specific coupling into SupervisorStateManager — the function needs only `{interventions, startedAt}`.

<!-- capsule-v2 -->
# Beat duration kernel — how does the compiler time every beat without a single hand-set duration?

**Source:** browser-harness-js MIT `main@6b189406`; Codebase Memory `browser-harness-js`. **Question:** Where do beat `dur` values come from when the edit brief never specifies timing?

## Reading-speed cards + floor-ladder action durations + self-aware budget padding

**Path/Symbol:** `skills/cdp/sdk/video.ts:cardDuration` (:182-186), `defaultActionDuration` (:229-238), `durationBudget` (:240-246), `addRawToCardHolds` (:248-260); consumed at `compileBrief` (:456,:464,:475,:482-487).
**Signature:** `cardDuration(title, summary?, details[], kind: 'intro'|'outcome'|'explanation', readingWpm): number`; `defaultActionDuration(beat: Json, pacing: Json): number`; `durationBudget(actionCount, explanationCount, rawToCardCount, pacing): number`.
**Data Shape:** every result passes through `round()` (ms precision, :188-190); pacing numbers come from `HOUSE_STYLE.pacing` (:31-39) — captionBaseSeconds 0.35, captionSecondsPerWord 0.2, rawToCardHoldSeconds 0.55, baseDurationBudget 22, extraActionSeconds 1.25, extraExplanationSeconds 3, maximumDurationBudget 32.

### Decisive source
```ts
function cardDuration(title, summary, details, kind, readingWpm) {
  const text = [title, summary, ...details].filter(Boolean).join(' ');
  const base = kind === 'intro' || kind === 'outcome' ? 4.5 : 4;
  return round(Math.max(base, 0.4 + words(text) * 60 / readingWpm));   // reading time at style wpm
}
function defaultActionDuration(beat: Json, pacing: Json): number {
  let base = 0.7;
  if (beat.click) base = 1.15;
  if (beat.after) base = Math.max(base, 1.4);
  if (beat.type) base = Math.max(base, 0.6 + String(beat.type.text || '').length * 0.035);
  if (beat.narration) {
    base = Math.max(base, Number(pacing.captionBaseSeconds) + Number(pacing.captionSecondsPerWord) * words(beat.narration));
  }
  return round(base);
}
```
and the budget that pays for its own padding:
```ts
const rawToCardCount = addRawToCardHolds(beats, pacing);   // inserts endStateHold AND returns count
const budget = durationBudget(brief.actions.length, explanations.length, rawToCardCount, pacing);
```

**Flow:** card beats get `max(kind floor, reading-time at style.readingWpm)` → each compiled action beat gets the MAX of its applicable floors (0.7 idle / 1.15 click / 1.4 with after-frame / per-char typing 0.035s / narration caption formula identical to the template's own caption pacing) → after all beats exist, adjacent raw→card pairs get `endStateHold` (+0.55s) added to `dur` and counted → budget = 22s + 1.25s per action beyond 5 + 3s per explanation beyond 1 + holds, hard-capped at 32s → total duration exceeding budget+0.001 throws with remediation copy (:485-487).
**Invariant:** (1) Timing is COMPUTED from content shape (word counts, typed-text length, event features) — an editor changes pacing by editing copy or HOUSE_STYLE, never by hand-tuning a beat. (2) Every action term is a max, not a sum: the slowest constraint wins and durations can't balloon multiplicatively. (3) The budget is charged for exactly the holds the compiler itself inserted (`rawToCardCount` feeds back into `durationBudget`), so structural padding can never trigger a false over-budget failure.
**Probe:** direct tests exercise the kernel only through compile shape assertions ('recording initialization hides typing…', video.test.ts :46-68); no dedicated duration assertions exist. Deterministic pins: `grep -n "function cardDuration\|let base = 0.7\|rawToCardCount \* Number(pacing.rawToCardHoldSeconds)\|maximumDurationBudget" skills/cdp/sdk/video.ts` → :182/:230/:244/:38.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-harness-js", query: "cardDuration", limit: 3, fields: ["lines"] });
// resolves video.cardDuration @ video.ts:182-186 (single hit)
```

## Verdict
Adopt computed-from-content durations plus a budget that accounts for its own structural padding wherever generated timelines must stay watchable without human timing; adapt the constants (380 wpm, 0.55s hold, 22–32s window) to your medium; omit the per-char typing term only if your renderer scrolls long text instead of holding.

<!-- capsule-v2 -->
# Schedule compiler + lossless preset recognizer — how do structured schedules and raw cron strings interconvert without ever changing firing behavior?

**Source:** localterm MIT `fix/pi-extension-native-import@f26c5853f4bed28f7a0cca14dd1c02f54b86d6fa`; Codebase Memory `localterm`. **Question:** How do I compile friendly schedule kinds to cron, recognize a cron back into a preset, and migrate bare-string APIs — with what proof that firing never changes?

## compileScheduleAll → recognizeCandidate → parse-equality safety net
**Path/Symbol:** `packages/server/src/utils/compile-schedule.ts:compileScheduleAll` (27–66), `detectStep` (92–101), `recognizeCandidate` (103–156), `recognizePreset` (158–169), `normalizeScheduleInput` (174–178).
**Signature:** `compileScheduleAll(schedule: AutomationSchedule): string[]`; `recognizePreset(expression: string): AutomationSchedule | null`; `normalizeScheduleInput(input: AutomationSchedule | string): AutomationSchedule`.
**Data Shape:** 8 schedule kinds; `timesOfDay` fans out to SEVERAL crons (one per distinct time, sorted earliest-first via `memoBy` dedupe); everything else is exactly one. Nothing derived is persisted — compilation runs on the fly.

### Decisive source
```ts
// :158-169 — the losslessness proof IS the accept gate
export const recognizePreset = (expression: string): AutomationSchedule | null => {
  const parsed = parseCronExpression(expression);
  if (!parsed) return null;
  const candidate = recognizeCandidate(parsed);
  if (!candidate) return null;
  // Parse-equality safety net: only single-cron candidates are recognized, so
  // the recompiled cron must re-parse set-equal to the original.
  const compiled = compileScheduleAll(candidate);
  if (compiled.length !== 1) return null;
  const recompiled = parseCronExpression(compiled[0]);
  return recompiled && parsedCronEqual(parsed, recompiled) ? candidate : null;
};
```

**Flow:** every kind compiles to canonical cron (`weekdaysPreset`→`1-5`/`0,6`, lists sort-unique). Recognition walks the inverse ladder: month field must be full wildcard (restricted month stays cron) → multi-minute set must be an exact `*/step` expansion (`detectStep`: starts at 0, uniform through max) over wild day fields ⇒ `everyNMinutes` → single minute + hour-step ⇒ `everyNHours` → single minute all-hours ⇒ `hourly` → one hour: dom∧dow wild ⇒ `daily`; dow-restricted ⇒ weekdays {1..5} / weekends {0,6} presets or generic `weekly`; dom-restricted ⇒ `monthly`. BOTH day fields restricted (Vixie OR) has NO preset — stays `{kind:"cron"}`. `parsedCronEqual` compares all five sets AND both restricted flags. `normalizeScheduleInput` recognizes a bare string, wraps unparseable ones as raw cron, and passes structured objects through verbatim — an explicit `{kind:"cron"}` STAYS advanced even when recognizable (caller chose the escape hatch).
**Invariant:** a candidate is accepted ONLY if it recompiles to a parse-set-equal cron; any divergence falls back to `{kind:"cron"}` byte-for-byte so migration can never alter firing. `compileSchedule()` (display/back-compat) returns `compileScheduleAll(...)[0]` — for timesOfDay that's the EARLIEST cron while the scheduler reads ALL of them.
**Probe:** `packages/server/tests/compile-schedule.test.ts` — `"compiles timesOfDay to one cron per distinct time, earliest first"` (:43), `"guarantees every recognized preset recompiles to a parse-equal cron"` (:89), `"falls back to null for ambiguous, restricted-month, or invalid crons"` (:103 pins `0 9 1 * 1` OR-rule fallback), `"keeps an explicit cron schedule advanced even when it is recognizable"` (:125).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "localterm", query: "compileScheduleAll recognizePreset", limit: 5, detail: "compact" });
// → recognizePreset @ compile-schedule.ts:158-169, compileScheduleAll @ :27-66
await mcp.codebase_memory.search_graph({ project: "localterm", query: "recognizeCandidate detectStep", limit: 5, detail: "compact" });
```

## Verdict
Adopt the compile/recognize pair plus the parse-equality accept gate verbatim — it is the reusable trick for any friendly-label-over-cron API; adapt the preset vocabulary (8 kinds) to host UX; omit `memoBy` if no dup-heavy inputs. 14 direct tests pin every branch at this commit.

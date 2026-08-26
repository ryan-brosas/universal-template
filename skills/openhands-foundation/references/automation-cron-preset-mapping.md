<!-- capsule-v2 -->
# Cron preset mapping — round-tripping cron strings to friendly schedule presets without silently rewriting unsupported expressions

**Source:** OpenHands / All-Hands-AI MIT `main@8511fff62d3084587cda1add483fe5ea9c8bfd7e`; Codebase Memory `openhands`. **Question:** How should a schedule editor decode only the cron shapes it can truly edit, and preserve everything else verbatim?

## Connected graph-selected seam
**Path/Symbol:** `src/utils/automation-schedule.ts:parseCronSchedule` (33–65) / `buildCronSchedule` (67–81); direct test `__tests__/utils/automation-schedule.test.ts`.
**Signature:** `parseCronSchedule(cron: string|null|undefined): ParsedSchedule`; `buildCronSchedule(input: PresetSchedule): string`; `parseTimeOfDay(v: string): {hour,minute}|null`.
**Data Shape:** `ParsedSchedule = PresetSchedule ({kind:"daily"|"weekdays"|"weekly", hour, minute, weekday?}) | CustomSchedule ({kind:"custom", raw, hour?, minute?})`.

### Decisive source
```ts
const minute = parseSingleInt(minuteField, 0, 59);   // SINGLE_INT = /^(\d+)$/ — NO lists, steps, ranges
const hour   = parseSingleInt(hourField, 0, 23);
if (minute === null || hour === null) return { kind: "custom", raw };
if (domField !== "*" || monthField !== "*") return { kind: "custom", raw, hour, minute };
if (dowField === "*" || dowField === "0-6") return { kind: "daily", hour, minute };
if (dowField === "1-5")                     return { kind: "weekdays", hour, minute };
const weekday = parseSingleInt(dowField, 0, 6);
if (weekday !== null)                       return { kind: "weekly", hour, minute, weekday };
return { kind: "custom", raw, hour, minute };         // everything uneditable keeps its raw string
```

**Flow:** UI loads an automation → `parseCronSchedule` recognizes EXACTLY five-field crons whose minute/hour are single ints, dom/month are `*`, and dow is `*`|`0-6`|`1-5`|single int → preset editors edit hour/minute/weekday → save runs `buildCronSchedule`, emitting canonical `${minute} ${hour} * * [*|1-5|dow]` via an exhaustive switch (`never` check) → anything unrecognized stays `kind:"custom"` carrying the original `raw`, so saving never rewrites a schedule the UI cannot express.

**Invariant:** Parse and build are inverse on presets (`build(parse(preset)) == preset` semantics); non-preset input is preserved byte-for-byte in `raw`; invalid times (`24:00`, `9-30`) reject as null rather than clamp.

**Probe:** Executed this pass against the REAL source under `node --experimental-strip-types` (file is dependency-free): `'0 9 * * *'`→daily 9:00, `'30 8 * * 1-5'`→weekdays 8:30, `'0 14 * * 3'`→weekly wd3, `'0 9,17 * * *'`/`'0 9 1 * *'`/`'every 5 minutes'`/`''`→custom=true, build emits canonical strings, weekdays roundtrip exact, `parseTimeOfDay('09:30')`→{9,30}, `'24:00'`/`'9-30'`→null — all matching the direct test. Exit 0.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openhands", query: "parseCronSchedule buildCronSchedule preset schedule roundtrip", limit: 6 });
// executed this pass -> parseCronSchedule src/utils/automation-schedule.ts 33-65,
// buildCronSchedule 67-81, PresetSchedule 3-8
```

## Verdict
Adopt strict-recognition-with-graceful-custom-fallback and canonical emission; adopt `parseTimeOfDay`'s reject-don't-clamp validation. Adapt preset vocabulary (monthly/yearly etc.) to your domain. Omit the OpenHands automation trigger/export validation layers around it. Coverage: `no_recorded_issue`; behavioral probe executed live as recorded.

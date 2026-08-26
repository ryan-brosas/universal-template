<!-- capsule-v2 -->
# Battery status parsing — what does the OS actually say about power, and when must the answer be "unknown"?

**Source:** localterm MIT `fix/pi-extension-native-import@f26c5853f4bed28f7a0cca14dd1c02f54b86d6fa`; Codebase Memory `localterm`. **Question:** How do I parse macOS `pmset -g batt` and Linux sysfs into one fail-open status shape without misreading AC time-to-full as time-to-empty?

## Dual-platform parser pair over a single BatteryStatus shape
**Path/Symbol:** `packages/server/src/caffeinate-battery.ts:parsePmsetBatt` (32–56), `parseSysfsBattery` (76–98), `clampBatteryPercent` (58–67), `defaultBatteryProbe` (152–153).
**Signature:** `parsePmsetBatt(stdout: string): BatteryStatus | null`; `parseSysfsBattery(files: { capacity: string; status: string; timeToEmptyNow?: string }): BatteryStatus | null`.
**Data Shape:** `BatteryStatus { percent: number; isOnBattery: boolean; minutesToEmpty: number | null }`; probe resolves null on no battery / missing binary / unparseable output — callers treat null as "don't gate".

### Decisive source
```ts
// :46-54 — the trap this capsule exists for
const isOnBattery = /Battery Power/.test(stdout);
let minutesToEmpty: number | null = null;
if (isOnBattery) {
  // Only trust the time estimate on battery: the AC "remaining" is time to
  // full charge, not to empty, and would blow up the adaptive scheduler.
  const timeMatch = TIME_RE.exec(stdout);
  if (timeMatch) minutesToEmpty = Number(timeMatch[1]) * 60 + Number(timeMatch[2]);
}
```

**Flow:** pmset path — `present: false` ⇒ null (desktop "No Batteries Available"); no `%` match ⇒ null; `isOnBattery = /Battery Power/` (the ONLY line meaning discharging — "AC Power" covers charging AND charged-plugged-in); time estimate trusted ONLY on battery. Linux path — readdir `/sys/class/power_supply`, pick the dir whose `type` reads exactly "Battery", read capacity/status/time_to_empty_now; strict `/^\d+$/` on capacity (NOT Number()+isFinite: `Number("")===0` would surface a malformed read as 0%); only exact `^Discharging$` gates; zero/negative seconds ⇒ null estimate. `clampBatteryPercent`: non-finite → MIN, floor fractionals, clamp [5,50].
**Invariant:** minutesToEmpty feeds the adaptive poll scheduler, so an AC time-to-CHARGE value in that field is not a display bug but a scheduler-corrupting wrong port; every malformed input resolves to null (fail-open upstream), never to a fabricated 0%/discharging state.
**Probe:** `packages/server/tests/caffeinate-battery.test.ts::"treats AC power as not-on-battery and drops the time estimate"` (:27), `"returns null when the battery is not present"` (:55), `"returns null when the capacity is empty, whitespace, or non-numeric"` (:134), `"ignores a zero time-to-empty as no estimate"` (:128); clamp table :75-92.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "localterm", query: "shouldActivate battery", limit: 8 });
// → parsePmsetBatt / parseSysfsBattery / probeSysfsBattery / defaultBatteryProbe @ caffeinate-battery.ts (all resolved)
```

## Verdict
Adopt the BatteryStatus shape + fail-open-null contract + both parsers' edge rules verbatim (pure functions, directly testable); adapt the pmset regexes if porting to other OS power CLIs; omit sysfs walking where the host exposes a battery API natively. Direct tests pin every branch incl. the desktop and malformed-read cases.

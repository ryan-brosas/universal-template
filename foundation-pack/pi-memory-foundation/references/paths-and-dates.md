<!-- capsule-v2 -->
# Paths & dates — local-calendar memory layout, dir resolution, daily-date validation

**Source:** pi-memory (MIT, `main@39e6b998a2279c8fad4a2c6c64e26828c1d6023e`); Codebase Memory `pi-memory`. **Question:** How does an agent resolve the memory directory and key files, and why must daily-log dates use the LOCAL calendar rather than UTC?

## Paths & dates
**Path/Symbol:** `index.ts:resolveMemoryDir` (50–58), `_setBaseDir` (67–73), `_resetBaseDir` (76–78), `ensureDirs` (84–88), `todayStr` (101–103), `yesterdayStr` (105–109), `nowTimestamp` (111–114), `isValidDailyDate` (130–135), `dailyPath` (137–142).
**Signature:** `resolveMemoryDir(env?: MemoryEnv): string`; `_setBaseDir(baseDir: string): void`; `todayStr()/yesterdayStr(): string`; `isValidDailyDate(date: string): boolean`; `dailyPath(date: string): string`.
**Data Shape:** `MemoryEnv` reads `PI_MEMORY_DIR`, `HOME`, `USERPROFILE`, `HOMEDRIVE`/`HOMEPATH`. Layout: `~/.pi/agent/memory/{MEMORY.md, SCRATCHPAD.md, daily/YYYY-MM-DD.md, recovery/*.json}`. `dailyPath` throws on an invalid date; `isValidDailyDate` rejects non-`YYYY-MM-DD` and impossible calendar dates.

### Decisive source
```ts
// localDateStr (97-99): LOCAL calendar day — toISOString() is UTC and would
// file every evening write (after 5pm PDT) under tomorrow's date.
function localDateStr(d: Date): string {
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}`;
}
export function todayStr(): string { return localDateStr(new Date()); }
export function yesterdayStr(): string {
  const d = new Date(); d.setDate(d.getDate() - 1); return localDateStr(d);
}

// isValidDailyDate (130-135): regex + round-trip so 2026-02-30 is rejected
export function isValidDailyDate(date: string): boolean {
  if (!DAILY_DATE_REGEX.test(date)) return false;
  const [y, m, d] = date.split("-").map(Number);
  const parsed = new Date(Date.UTC(y, m - 1, d));
  return parsed.getUTCFullYear() === y && parsed.getUTCMonth() === m - 1 && parsed.getUTCDate() === d;
}
```

**Flow:** (1) `resolveMemoryDir` honors `PI_MEMORY_DIR`, else derives `~/.pi/agent/memory` from the platform home env. (2) `_setBaseDir` recomputes all four path constants (used as the test seam). (3) `ensureDirs` mkdirs memory/daily/recovery recursively. (4) All daily-log writes use `todayStr()` so the injected "today's log" and the written file always agree on the user's local day.

**Invariant:** daily-log keys are the user's LOCAL calendar date, never UTC; a date string is only trusted after both regex and calendar round-trip validation (prevents path traversal and impossible dates).

**Probe:** `test/unit.test.ts` — `local calendar dates` describe (:2052): `todayStr returns the LOCAL calendar date, not UTC` (:2055), `yesterdayStr returns the LOCAL calendar date minus one day` (:2061), `nowTimestamp uses local date and local hour` (:2068); `dailyPath` describe (:402) and `resolveMemoryDir` describe (:250). Coverage caveat: `test/` is excluded from the index by design, so probes are source-grounded from the on-disk test files.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-memory", query: "resolveMemoryDir todayStr isValidDailyDate dailyPath", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the local-calendar date helpers, the `PI_MEMORY_DIR`-override resolution, the strict daily-date validation, and the `_setBaseDir` test seam. Adapt the memory directory layout and env-var names to the host. Omit nothing here — this is the portable path/date core.

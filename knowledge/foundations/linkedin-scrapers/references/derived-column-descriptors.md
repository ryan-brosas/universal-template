<!-- capsule-v2 -->
# Derived column descriptors in table repos — how do I keep a computed flag (like day-and-night) in sync with the raw columns it derives from, across insert AND read, without triggers or double-writes?

**Source:** lh-basis (Linked Helper extract) NO LICENSE — learn-only, patterns recorded, zero code copied `extract mtime 2026-08-15`; Codebase Memory project `lh-basis` (dist plane outside roots — direct source probes). **Question:** when a stored row must carry a denormalized boolean derived from two other columns (start/end → wrapsMidnight), where do the conversion hooks live so every write path and read path stays consistent?

## Column descriptor `toColumn`/`fromRow` converters + AutoDates auto-columns

**Path/Symbol:** `WorkIntervals/WeekWorkingIntervalRepo.js:weekWorkingIntervalRepo` (descriptor for column `day_and_night`); twin `WorkingHoursAdjustments.js:workingHoursAdjustmentsRepo` (`isEnabled` 1↔true); base `DBModel/DBModelsRepo.js:DBModelsRepo` ctor (`getPropColumnsData`, `propToColumNamesMap`, `primaryKeyInfo` guard, `insertAutoDatesPropNames`/`updateAutoDatesPropNames` sets); schema pin `migrations/34.js:day_and_night INTEGER NOT NULL DEFAULT 0`.
**Signature:** descriptor entry = `{type:"column", columnName, storageType?, unique?, primaryKey?, toColumn?:(model)=>any, fromRow?:(row)=>any}`; `modelFromData(data) -> Model` per repo.
**Data Shape:** `dayAndNight: {columnName:"day_and_night", toColumn:({start,end}) => WeekWorkingSchedule.isDayAndNight({start,end}) ? 1 : 0, fromRow:({started_at,ended_at}) => isDayAndNight(...)}`; `isEnabled: {toColumn:(m)=>m.isEnabled?1:0, fromRow:(r)=>r.is_enabled===1}`.

### Decisive source
```js
// The DERIVED column never reads model.dayAndNight — it recomputes from its
// sources on EVERY crossing of the boundary, both directions:
dayAndNight: {
  type: "column",
  columnName: "day_and_night",
  toColumn: ({ start, end }) =>
    WeekWorkingSchedule.isDayAndNight({ start, end }) ? 1 : 0,   // write path
  fromRow: ({ started_at, ended_at }) =>
    WeekWorkingSchedule.isDayAndNight({ start, end })            // read path (same fn)
}
// isEnabled twin — bool model field ↔ INTEGER storage:
isEnabled: { toColumn: ({ isEnabled }) => isEnabled ? 1 : 0,
             fromRow: ({ is_enabled }) => 1 === is_enabled }
```

**Flow:** repo construction parses the descriptor table once into `propToColumNamesMap` / storage-type map / unique info / primary-key info (loud throw if no PK) and partitions auto-date columns into insert/update/delete sets → `insert()` fills model defaults, applies auto-dates per row group, runs each property through its `toColumn` when building parameter rows, chunks by present-column sets, emits `INSERT … ON CONFLICT(cols) DO NOTHING RETURNING …` → reads map raw snake_case rows back through `fromRow` (falling back to identity) then `modelFromData` to hydrate domain models.
**Invariant:** a derived column's converter must call the SAME predicate on both sides — duplicating the logic (a SQL CASE in one migration plus JS in the other) lets them drift after any rule change. Converters destructure their SOURCE fields (`{start,end}` / `{started_at,ended_at}`), which encodes the dependency explicitly: if you add a third input to the derivation, the converter signature forces you through every call site. Boolean storage normalizes at the boundary only (JS truthiness never touches SQL integers mid-query). The base repo treats converters as optional per column — plain columns skip them by identity, so adding a derived column cannot perturb sibling columns' wire format.
**Probe:** no public tests (proprietary extract) — coverage caveat. Deterministic probes verified at extract (lh-basis dist files are MINIFIED single-line — `grep -c` counts LINES not matches; use `grep -o … | wc -l` for occurrence counts): `grep -cF 'toColumn:({start:e,end:t})' WorkIntervals/WeekWorkingIntervalRepo.js` ⇒ 1 with twin `fromRow:({started_at:e,ended_at:t})` ⇒ 1 (dayAndNight pair keyed by the same descriptor; the boolean recompute `isDayAndNight({start:e,end:t})?1:0` appears once); `grep -oF 'toColumn:({isEnabled:e})=>e?1:0,fromRow:({is_enabled:e})=>1===e' WorkingHoursAdjustments.js | wc -l` ⇒ 1 (isEnabled pair on ONE line); `grep -oP "day_and_night INTEGER NOT NULL DEFAULT 0" migrations/34.js` pins the storage twin created by the table-rebuild migration; graph anchor resolves via semantic query "create working_intervals table day_and_night column" in project `lh-basis-migrations` (top hits migrate Functions 42/44).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "lh-basis-migrations", semanticQuery: ["create working_intervals table day_and_night column"], limit: 10 });
```

## Verdict
Adopt descriptor-level derive-on-write/read converters over triggers, generated columns, or write-site duplication whenever the deriving logic lives in application code — especially for flags like wraparound that depend on TWO nullable columns. Adapt to ORMs by mapping `toColumn/fromRow` onto value converters/column transformers; if your ORM has native generated columns, prefer those and drop the JS side. Omit the minified base-repo internals (chunking details are implementation, the CONTRACT is the descriptor). Contrast schema-typed-coercion-ladder (config-input coercion — this capsule is persistence-boundary coercion; same "convert exactly at the edge" principle).

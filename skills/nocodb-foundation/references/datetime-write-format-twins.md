<!-- capsule-v2 -->
# Date/Time write-format twins — why does a Date filter bind bare dates while Time pins HH:mm:ss, and how do dialects shift the storage timezone?

**Source:** NocoDB Sustainable Use License `develop@f7513664`; Codebase Memory `nocodb`. **Question:** How do the DateTime subclasses change comparison formats and write normalization per column family and per engine?

## DateGeneralHandler + TimeGeneralHandler + dialect parseUserInput
**Path/Symbol:** `date/date.general.handler.ts` — dateValueFormat='YYYY-MM-DD' :81; date-normalizing parseUserInput :21-69; comparisonBetween :83-112; filterByOperation factory :138-166. `time/time.general.handler.ts` — getTimeFormat 'HH:mm:ss' rationale :18-28; triple-fallback time parse :50-74. `date-time/date-time.pg.handler.ts` :26 (AT TIME ZONE, file 32L); `date-time.mysql.handler.ts` :38 (CONVERT_TZ) + comparisonBetween/comparisonOp overrides :49/:74.
**Signature:** `DateGeneralHandler extends DateTimeGeneralHandler` overriding comparisonBetween/comparisonOp to drop `.utc()` and use the bare-date format; `TimeGeneralHandler extends GenericFieldHandler`.
**Data Shape:** Date parseUserInput returns `value.match(/^\d{4}-\d{2}-\d{2}/)[0]` when the input starts ISO — "Normalize Date values to YYYY-MM-DD to prevent timezone conversion from shifting the date by ±1 day" (:60-62).

### Decisive source
```ts
// time.general.handler.ts :22-28 — why bare time:
// A `Time` column is time-of-day only. Emitting a full `YYYY-MM-DD HH:mm:ssZ`
// value breaks comparison against a real `time` column on PG ("invalid input
// syntax for type time") and date-mismatches on sqlite (a filter value like
// "02:02:00" defaults to today while stored rows carry 1999-01-01).
// date-time.mysql.handler.ts :40-42 — matching the group-by normalization:
// Normalize the column to UTC before comparing, so the WHERE clause matches
// the same CONVERT_TZ normalization used in the group-by SELECT.
knex.raw("CONVERT_TZ(??, @@GLOBAL.time_zone, '+00:00') between ? and ?", [...])
// pg: knex.raw(`? AT TIME ZONE CURRENT_SETTING('timezone')`, [utcValue])
```

**Flow:** Date ops compare `col = 'YYYY-MM-DD'` directly via a filterByOperation(op) curried factory binding this; neq adds orWhereNull. Time parses full-datetime → HH:mm:ss → `'1999-01-01 ' + value` fallback ladder in verifyFilter, filter, AND parseUserInput so read/write agree. DateTime writes: PG converts UTC→db tz via CURRENT_SETTING; MySQL via CONVERT_TZ(?, '+00:00', @@GLOBAL.time_zone); SQLite keeps the offset-suffixed string; mssql/oracle inherit general.
**Invariant:** (1) MySQL's comparison override is symmetric with its group-by SELECT — without CONVERT_TZ on the COLUMN side, UTC filter values vs raw stored values yield empty groups. (2) The 1999-01-01 sentinel prefix is a parse aid only — getTimeFormat strips it back off. (3) TimeMysqlHandler ALONE re-widens to 'YYYY-MM-DD HH:mm:ss' because MySQL TIME comparisons against bare times misbehave with its session format.
**Probe:** No unit tests upstream at pin. Deterministic probe: grep "shifting the date by ±1 day"; search_graph resolves `DateGeneralHandler.comparisonBetween` line-exact.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "DateGeneralHandler", limit: 5 });
```

## Verdict
Adopt per-family format pinning + symmetric normalize-on-both-sides rule; adapt tz functions to your engines; omit nothing. Caveat: no direct tests at pin.

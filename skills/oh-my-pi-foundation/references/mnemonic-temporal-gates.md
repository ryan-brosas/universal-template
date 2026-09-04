<!-- capsule-v2 -->
# Mnemonic temporal recall + feature gates — deterministic time, explicit opt-in

**Source:** Oh My Pi MIT `main@96f428097`; Codebase Memory project `oh-my-pi` (code-grounded). **Path:** `packages/mnemopi/src/core/temporal-parser.ts`, `core/beam/recall.ts` (+ `helpers.ts`), `config.ts`. **Question:** How does natural-language time stay deterministic and rerank-only, and how do optional recall features stay off until explicitly enabled?

## Temporal parser: deterministic relative and absolute dates
**Path/Symbol:** `temporal-parser.ts:parseNlDate` (173–329), `extractTemporal` (331–359), `extractDateFromText` (361), `resolveRelativeDay` (120); `beam/recall.ts:parseQueryTime` (397, re-exported via helpers), `temporalBoost` (415–422; canonical impl in `beam/helpers.ts:174–188`).
**Signature:** `parseNlDate(text, reference?): ParsedNaturalDate | null`; `extractTemporal(text, reference?): TemporalInfo`; `temporalBoost(timestamp, queryTime, halfLifeHours): number`.
**Data Shape:** `ParsedNaturalDate = [eventDate: Date, precision: Exclude<DatePrecision,"unknown">, temporalTags: string[]]`; `TemporalInfo { event_date: string|null, event_date_precision: "day"|"week"|"month"|"year"|"relative"|"unknown", temporal_tags: string[], primary_signal: string|null }`. UTC-normalized reference resolution keeps parsing deterministic.

### Decisive source
```ts
export function temporalBoost(timestamp: unknown, queryTime: Date, halfLifeHours: number): number {
  const raw = asString(timestamp);
  if (raw.length === 0) return 0;
  const parsed = Date.parse(raw);
  if (!Number.isFinite(parsed)) return 0;          // invalid timestamps contribute nothing
  const distanceHours = Math.max(0, queryTime.getTime() - parsed) / 3_600_000;
  return Math.exp(-distanceHours / Math.max(halfLifeHours, 0.001));
}
```

**Flow:** parsing normalizes the caller-supplied or default reference to UTC and resolves explicit dates, relative weekdays (`last/this/next` qualifiers), `n` day/week/month/year intervals (past and future), named dayparts (`morning`…`dusk`), and vague markers (`recently`, `a while ago`). Recall applies it twice: `inferTemporalOptions` turns a recognized event date into a query-time reference + default `temporalWeight=0.35`; `scoreCandidate` multiplies by `1 + temporalWeight · max(recencyBoost, eventBoost)` where the event-date boost runs at 2× half-life. A future timestamp clamps to the newest value (`Math.max(0,…)` ⇒ boost 1) rather than erroring.

**Invariant:** the parser is deterministic for a supplied reference; no recognized phrase yields `unknown` precision with a null date; malformed timestamps score 0 instead of throwing. Temporal scoring never adds or removes candidates — it only adjusts rank.

**Probe:** `test/temporal-parser.test.ts` pins parsing, boundaries, tags, and UTC; `test/temporal-recall.test.ts` pins `temporalBoost` decay, invalid/future timestamps, and rank-only effects.

## Feature gates: host defaults with env override in both directions
**Path/Symbol:** `config.ts:configureRecallFeatures` (288–292), `enhancedRecallEnabled` (303–306), `polyphonicRecallEnabled` (294–297), `proactiveLinkingEnabled` (308–311), `temporalHalflifeHours` (299–301).
**Signature:** `configureRecallFeatures(flags: RecallFeatureFlags): void`; gate functions accept `env = process.env` and return `boolean`.
**Data Shape:** `RecallFeatureFlags { polyphonicRecall?, enhancedRecall?, proactiveLinking? }`; gates default OFF; env vars `MNEMOPI_POLYPHONIC_RECALL`, `MNEMOPI_ENHANCED_RECALL`, `MNEMOPI_PROACTIVE_LINKING`, `MNEMOPI_TEMPORAL_HALFLIFE_HOURS` (default 24).

### Decisive source
```ts
export function enhancedRecallEnabled(env: Env = process.env): boolean {
  const value = envOptionalString("MNEMOPI_ENHANCED_RECALL", env);
  return value === undefined ? enhancedRecallDefault : value === "1";
}
```

**Flow:** host configuration (`configureRecallFeatures`) sets only supplied process-wide defaults; each read resolves the CURRENT env, and `"0"`/`"1"` overrides the default in BOTH directions — env `"0"` disables a host-enabled feature, env `"1"` enables a host-disabled one. The temporal half-life is a pure env float with a fixed default.

**Invariant:** gates are explicit opt-in and never silently widen behavior; an env-pinned feature cannot be flipped back by later config — precedence is env > config-default, resolved per read.

**Probe:** `test/recall-feature-flags.test.ts` pins default-off, partial updates, and env-over-configured precedence in both directions.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", name_pattern: "^(parseNlDate|extractTemporal|extractDateFromText|resolveRelativeDay|parseQueryTime|temporalBoost|configureRecallFeatures|enhancedRecallEnabled|temporalHalflifeHours)$", limit: 10, fields: ["signature"] });
```

## Verdict
Adopt UTC-anchored deterministic NL dates, exponential-decay temporal boosting that only reranks, and env-over-config feature gates resolved per read; adapt the phrase grammar, env var names, and defaults to host; omit the specific tag vocabulary unless porting the whole recall stack.

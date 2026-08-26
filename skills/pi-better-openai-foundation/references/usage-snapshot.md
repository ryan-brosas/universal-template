<!-- capsule-v2 -->
# Usage snapshot — parse and format ChatGPT subscription usage windows (left-percent, reset countdown/clock, Spark scope)

**Source:** pi-better-openai (MIT, `main@86814e9047996abba08e4c907e23286329196fe0`); Codebase Memory `pi-better-openai`. **Question:** How does an extension turn the ChatGPT `/backend-api/wham/usage` response into a stable snapshot of remaining 5-hour and 7-day usage percentages plus reset times, handling a Spark-specific bucket and formatting a compact countdown + local reset clock?

## Usage snapshot parsing and formatting
**Path/Symbol:** `src/usage.ts:parseUsageSnapshot` (205–224), `formatUsageSnapshot` (232–256), `requestCodexUsage` (129–147); helpers `normalizeRateLimitBucket` (149–162), `findSparkRateLimitBucket` (170–187), `getResetSeconds` (189–199), `formatResetCountdown` (84–95), `formatResetClock` (97–112), `formatCompactReset` (114–123), `usedToLeftPercent` (79–82), `clampPercent` (75–77), `usageScopeForModel` (201–203).
**Signature:** `parseUsageSnapshot(data: CodexUsageResponse, modelId: string | undefined, now?): UsageSnapshot`; `formatUsageSnapshot(snapshot, options: { showResetTimes: boolean }, now?): string`; `async requestCodexUsage(ctxOrSignal?, signal?): Promise<CodexUsageResponse | undefined>`.
**Data Shape:** `UsageSnapshot = { capturedAt, scope: "default"|"spark", fiveHourLeftPercent, sevenDayLeftPercent, fiveHourResetInSeconds, sevenDayResetInSeconds, isLimited }`. `CodexUsageResponse = { rate_limit?: RateLimitBucket|null, additional_rate_limits?: ... }`; `RateLimitBucket = { allowed?, limit_reached?, primary_window?: UsageWindow|null, secondary_window?: UsageWindow|null }`; `UsageWindow = { used_percent?, reset_after_seconds?, reset_at? }`. `USAGE_URL = "https://chatgpt.com/backend-api/wham/usage"`.

### Decisive source
```ts
// usedToLeftPercent: convert used% to remaining%, clamped to [0,100]
return clampPercent(100 - value);

// getResetSeconds: prefer reset_after_seconds, else derive from reset_at (ms vs s)
if (typeof window?.reset_after_seconds === "number" && Number.isFinite(window.reset_after_seconds))
  return window.reset_after_seconds;
if (typeof window?.reset_at !== "number" || !Number.isFinite(window.reset_at)) return null;
const resetAtSeconds = window.reset_at > 100_000_000_000 ? window.reset_at / 1000 : window.reset_at;
return Math.max(0, resetAtSeconds - now / 1000);

// parseUsageSnapshot: Spark scope reads the Spark bucket, else base rate_limit
const bucket = scope === "spark"
  ? (findSparkRateLimitBucket(data) ?? normalizeRateLimitBucket(data.rate_limit))
  : normalizeRateLimitBucket(data.rate_limit);
isLimited: bucket?.limit_reached === true || bucket?.allowed === false,

// formatResetCountdown: compact d/h/m/s
if (days > 0) return `${days}d${hours}h`;
if (hours > 0) return `${hours}h${minutes}m`;
if (minutes > 0) return `${minutes}m`;
return `${secs}s`;
```

**Flow:** (1) `requestCodexUsage` resolves credentials (see codex-auth capsule), fetches `USAGE_URL` with `authorization: Bearer <token>` and `chatgpt-account-id`, throws on non-ok status; (2) `parseUsageSnapshot` picks the Spark bucket when the model is `gpt-5.3-codex-spark` (falling back to base `rate_limit`), else the base bucket; (3) computes left-percents and reset seconds; (4) `formatUsageSnapshot` renders `Usage: 5h: <pct> | 7d: <pct>` plus, when `showResetTimes`, `5h ↺ <countdown> - <clock>` and `7d ↺ ...`; the countdown decrements with elapsed time while the reset clock stays fixed (cached `Intl.DateTimeFormat` per timezone).

**Invariant:** percentages are always clamped to [0,100] and rendered as `--` when absent; a non-finite reset value yields `null` (never NaN); the reset countdown decreases over time but the absolute reset clock does not move; Spark scope falls back to the base bucket when no Spark-specific limit is present.

**Probe:** `tests/usage.test.ts` — `parses and formats usage snapshots` (`used_percent:1` → `fiveHourLeftPercent:99`, `49` → `sevenDayLeftPercent:51`, format matches `/^Usage: 5h: 99% \| 7d: 51%$/`); `decrements reset countdowns without moving the reset clock` (1h0m → 30m → 0s, clock segment identical); `refreshes cached reset-clock formatters when the time zone changes`; `falls back to the base rate limit when Spark-specific usage is absent` (Spark model → scope `"spark"`, percents from base bucket). Coverage caveat: `tests/` is excluded from the index by design (`fast-pattern`), so these probes are source-grounded from the on-disk test file, not graph-covered.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-better-openai", query: "parseUsageSnapshot formatUsageSnapshot requestCodexUsage formatResetCountdown usageScopeForModel", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the bucket normalization, the used→left-percent conversion with clamping, the reset-seconds derivation (prefer `reset_after_seconds`, handle ms/s `reset_at`), the compact countdown + fixed clock formatting, and the Spark-scope fallback. Adapt the usage endpoint, the Spark model id/limit name, and the display wording to the host. Omit the `UsageController` polling lifecycle (tightly coupled to pi's `ExtensionContext` events) unless a target needs it.

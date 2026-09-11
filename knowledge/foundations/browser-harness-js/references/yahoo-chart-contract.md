<!-- capsule-v2 -->
# Yahoo v8 Chart Contract — snapshot vs history, previous_close semantics

## Source
Repo: browser-harness-js @ main`6b18940` (unchanged vs base_sha).

## Question
How does findata serve `price` (snapshot) and `prices` (history) from one endpoint, and which meta field is the correct "previous close"?

## Path / Symbol
`skills/findata/scripts/findata` :189-196 (URL assembly), :193 (price expr), :198-232 (projection + pretty render); SKILL.md Result shapes + Traps.

## Signature
```js
// One endpoint: query1.finance.yahoo.com/v8/finance/chart/<TICKER>?interval=&range=
//   price  ⇒ forced interval=1d&range=5d (fixed window; snapshot derived from it)
//   prices ⇒ --range R or --period1/--period2 unix seconds (--start/--end parsed via node Date.parse)
// Projection: rows = timestamps × quote[0] arrays, skipping null open+close bars;
//   adjclose joined when present. Meta: regularMarketPrice, chartPreviousClose, currency,
//   exchangeName/fullExchangeName, longName||shortName, regularMarketTime.
// Snapshot derivation:
const prev = prices.length >= 2 ? prices[prices.length-2].close : chartPreviousClose;
change = price - prev;  change_percent = prev ? change/prev*100 : null;
```

## Data Shape
price → `{ticker,name,price,previous_close,change,change_percent,currency,exchange,time}`; prices → `{ticker,name,currency,interval,prices:[{date,open,high,low,close,volume,adj_close}]}` with ISO dates sliced from epoch seconds.

## Decisive source
SKILL.md result-shape note: "`previous_close` is the prior trading day's close (**derived from the second-to-last daily bar** of a 5-day window), not the start-of-range close — so `change` is the true day-over-day move." And the trap entry: "**`chartPreviousClose` in Yahoo's meta is the close *before the range start* (~5 days ago), not yesterday — that's why it isn't used**" (only as fallback when <2 bars). Rate-limit surfacing: non-JSON page becomes error "Yahoo Finance error … non-JSON response (possibly rate-limited)" — the browser transport sidesteps crumb/consent walls but not volume limits. Ticker normalization `.`→`-` applied before both SEC and Yahoo calls (:86, :90).

## Flow / Invariant
1. Snapshot IS a small history query — one endpoint, one transport path (navJsonFetch) for both commands.
2. Day-over-day change requires the second-to-last BAR, never range-start meta.
3. Null-bar skipping must pair open AND close checks so halted sessions don't emit empty rows.

## Probe (direct tests)
Deterministic probes at pin (ERRATUM pass-5 execution audit — original anchors mis-modeled the projection's naming; counts below live-executed against source at unchanged pin `main@6b189406`): `grep -c 'chart_previous_close' skills/findata/scripts/findata` → 2 lines (:192 wire-side priceExpr reads Yahoo meta camelCase `chartPreviousClose`, :197 projection fallback reads snake_case) and `grep -c 'chartPreviousClose' skills/findata/scripts/findata` → 1 line (:192 only; the shipped claim "→ 2" was wrong because the script's own projection RENAMES meta to snake_case — a porter grepping only camelCase misses the real fallback at :197). `grep -o "regularMarketPrice" skills/findata/scripts/findata | wc -l` → 2 occurrences on 2 lines (:192 expr, :198 JSON projection) — prior erratum said 1; that too was line-count confusion on the multi-occurrence :192. Smoke harness scripts/test for live runs. Live Yahoo verification blocked in sandbox — values pinned from source + SKILL.md examples.

## Retrieve
grep-first (`v8/finance/chart`, `chartPreviousClose`, `adjclose`).

## Verdict
ADOPT: the endpoint unification and the previous-close bar rule are the reusable contract; everything else is presentation.

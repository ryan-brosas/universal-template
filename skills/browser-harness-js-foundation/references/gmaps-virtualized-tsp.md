<!-- capsule-v2 -->
# Gmaps Virtualized TSP — straight-line edges, one real directions call

## Source
Repo: browser-harness-js @ main`6b18940` (unchanged vs base_sha).

## Question
How does `gmaps --optimize` produce a fastest visiting order without paying for an N² directions matrix?

## Path / Symbol
`skills/gmaps/scripts/gmaps` :407-455 (REPL-side helpers), :415-438 (Held-Karp), :508-530 (optimize mode orchestration); resolvePlace :396-411.

## Signature
```js
// 1. Resolve each place to EXACT lat/lng — a place-name search renders NO results feed;
//    the page URL itself updates to /maps/place/...!8m2!3d<lat>!4d<lng>... and
//    "the !3d!4d token is the place's EXACT coordinates (the @lat,lng is only the
//    viewport region)". Poll location.href for up to 20s. N parallel background tabs.
// 2. Build the haversine distance matrix (R=6371km) over resolved coords.
// 3. Exact open-path TSP with FIXED start (node 0): Held-Karp DP over subsets of {1..n-1},
//    n<=12, path may end anywhere:
function tspOpenPathFixedStart(d){ /* dp[mask][j] = min cost visiting mask, ending j;
   init dp[1<<(j-1)][j]=d[0][j]; transitions skip k in mask; final best over dp[full][j];
   path reconstructed via par[] with mask ^= (1<<(cur-1)) */ }
// 4. ONE real directions() call for the chosen order → "the reported time is real even
//    though the order is an estimate". Legs report km + bearing + compass8 direction.
```

## Data Shape
Optimize JSON result carries `places` (resolved coords+urls), `order` (names), `order_indices`, per-leg `{from,to,km,bearing,dir}`, `straight_line_total_km`, and the REAL `route` object, plus an explicit honesty note string: "Order is a best-effort estimate from straight-line (haversine) distances; the <mode> time/distance is the real route for that order."

## Decisive source
Usage comment :16-23: "each place -> lat/lng (search), straight-line haversine matrix -> open-path TSP (fixed start = first place) -> one real directions call for the chosen order... so the reported time is real even though the ORDER is a straight-line estimate. Up to 12 places." resolvePlace comment :396-400 pins the URL-token coordinate source and that this is safe to run N-of in parallel ("each owns its own background tab"). Guard rails: `--optimize >12 places` rejected pre-browser (:131-133) because Held-Karp is O(2^n·n²).

## Flow / Invariant
Virtualize the expensive edges (straight-line), then validate the RESULT with exactly ONE real measurement; never present the estimated order's cost as travel time. Fixed-start open-path (not closed loop) matches how users ask ("starting at X, visit these").

## Probe (direct tests)
gmaps smoke test runs optimize live: expects "Optimized route" header, per-leg km, "Real driving for this order", the "best-effort" note, and `/maps/dir/` url; guard test asserts >12 places fails deterministically without launching a browser. Deterministic probe at pin: `grep -c "tspOpenPathFixedStart" skills/gmaps/scripts/gmaps` → 2.

## Retrieve
grep-first (`tspOpenPathFixedStart`, `haversineKm`, `resolvePlace`); graph covers SDK session plane used by each parallel resolvePlace tab.

## Verdict
ADOPT the virtualize-then-validate pattern for any expensive-matrix routing problem; keep the honesty-note contract in output.

<!-- capsule-v2 -->
# Readiness Ladder per Site Class — networkIdle / feed-count / duration-regex / commit

## Source
Repo: browser-harness-js @ main`6b18940` (unchanged vs base_sha).

## Question
When does each readiness signal work, and what does a porter get wrong by defaulting to `networkIdle` everywhere?

## Path / Symbol
- gsearch/gnews/xsearch: arm-before-navigate lifecycle wait (`scripts/gsearch` :150-158, `gnews` :92-99, `xsearch` :50-56).
- gmaps search feed poll :160-176; gmaps directions duration poll :243-258 + null→non-null mode re-render poll :318-330.
- ytdl/ttdl player+metadata polls (:141-166, ttdl :196-262).
- rsearch origin-commit wait :131-152.

## Signature
```js
// Arm BEFORE navigate — lifecycle events fire once; a fast load can fire
// networkIdle between navigate returning and the listener subscribing.
await cdp(sid,'Page.setLifecycleEventsEnabled',{enabled:true});   // REQUIRED: without it Chrome emits zero lifecycleEvent
const ready = session.waitFor({method:'Page.lifecycleEvent', sessionId,
  predicate:(p)=>p.name==='networkIdle', timeoutMs:30000});
await cdp(sid,'Page.navigate',{url});
await ready;
```

## Decisive source (why each class needs its own signal)
1. **networkIdle works**: plain HTML results pages (google.com/search, x.com after a fixed 4s hydration sleep + scroll loop for count>6).
2. **networkIdle NEVER fires — Maps**: gmaps :161-163 "Chrome never emits networkIdle for Maps (continuous XHR polling keeps the network quiet-window from ever opening), so we wait for the results feed to actually contain results" → poll `document.querySelectorAll("a[href*='/maps/place/']").length > 0`, then scroll the `div[role=feed]` with a two-consecutive-no-growth stop and 25-scroll cap.
3. **networkIdle never fires — Directions panel**: poll panel text for `/\d+\s*min\b/` OR a distance leaf (`/165 miles/`) so exact-hour routes aren't missed; the regex deliberately matches only the route list, not the compact travel-mode tabs ("2h 30m").
4. **Mode-switch re-render race**: after clicking a travel-mode tab the panel CLEARS then repopulates → poll null → sawNull → non-null ("no race against the previous mode's duration"); if still null after 15s the mode is unavailable (disabled-tab DOM can lag, so unavailability is detected from the absent route instead).
5. **Player boot** (ytdl :142-155): poll `<video>` AND `#movie_player` up to 60s, explicitly NOT requiring duration>0 yet ("metadata loads only once the player starts fetching, which may need the play nudge"); bot-interstitial sniff (`/unusual traffic|Are you a robot/i`) throws immediately; separate ≤20s metadata poll for `duration>0`.
6. **SPA origin-commit** (rsearch): main-frame-only frameNavigated matching an origin regex — enough for same-origin fetch.

## Flow / Invariant
The ladder is ordered by specificity: event-based when events exist; semantic-DOM polling when they don't; commit-level when only the origin matters. Every poll has a deadline AND a bail-fast error path (consent wall / no-results message includes the query).

## Probe (direct tests)
gmaps smoke test pins the semantics live: transit London→Paris must return "2 hr 18 min" while driving mode must NOT leak it (`refuse "mode driving: transit leak" "2 hr 18 min"`); unavailable cycling route must exit non-zero with "not available for this route". Deterministic probes at pin (ERRATUM pass-5 execution audit: shipped as "→ 1 each"; live counts at unchanged pin `main@6b189406` are gsearch **3 lines** (:102 lifecycle-wait helper call, :165 comment, :169 networkIdle arm) and gnews **2 lines** (:65 comment, :67 enable call) — comment-line contamination, re-derived against source): `grep -c "setLifecycleEventsEnabled" skills/gsearch/scripts/gsearch skills/gnews/scripts/gnews`.

## Retrieve
`search_graph --project browser-harness-js --semantic-query '["waitFor"]'` resolves session.waitFor overloads (session.ts:279-300) incl. the sessionId-scoped form that prevents cross-tab cross-fire.

## Verdict
ADOPT the four-signal taxonomy; the arm-before-navigate rule and the Maps XHR explanation are the two details porters get wrong.

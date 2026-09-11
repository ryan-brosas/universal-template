<!-- capsule-v2 -->
# gmaps Directions Panel Extraction — duration/distance/via/waypoints by leaf heuristics

## Source
Repo: browser-harness-js @ main`6b18940` (unchanged vs base_sha).

## Question
How does gmaps read the real route numbers (time with traffic, distance, via, tolls) from the rendered Directions panel?

## Path / Symbol
`skills/gmaps/scripts/gmaps` EX extraction IIFE :336-386 (readiness :243-258 and DURP re-render poll :302-330 feed it); waypoint inputs :379-381.

## Signature
```js
// Duration: first LEAF (childless element) matching
//   /^\d+\s*(min|hr|days?|h)(\s+\d+\s*(min|hr|days?|h))*$/   e.g. "2 hr 18 min"
//   NOT inside a radio (inRadio walks parentElement for role=radio — excludes tab labels)
//   Scope: [aria-label="Directions"] panel; WHOLE BODY when mode==='flights' (flight card is outside the panel).
// Distance: within the duration's ROUTE CARD — walk up ≤8 ancestors until one contains a
//   distance leaf /^[\d,]+(?:\.\d+)?\s*(miles|mi|km|ft|m)$/ — then read it. Scoping to the card,
//   not the panel, avoids grabbing another route's distance.
// via / label / tolls: panel-wide leaf scans anchored on text shapes:
//   /^via\s/, /^Fastest route/, /^This route has tolls\.?$/
// Waypoints: input[aria-label] matching /^(?:Starting point|Destination)\s+(.*)$/
```

## Data Shape
Result `{duration, distance, via, label, tolls, waypoints[], url}` where url is `location.href` (the /maps/dir/ deep link reproducing the query). Error path returns `{error}` in-band so readiness context can be appended ("(the Directions panel did not become ready in time — possible consent wall, or no route for this mode)").

## Decisive source
The card-ancestor-walk (:355-362) exists because the panel lists MULTIPLE routes: "walk up at most 8 ancestors looking for an element that contains a distance-format leaf; use that card as the scope" — without it, `distance` could come from a non-selected alternative route below the selected one. The `durScopeIsBody` flights exception (:287-288, :305-310) is documented at both selection and extraction sites ("Flights render their duration in a flight card OUTSIDE the Directions panel"). The duration regex's compact-form exclusion (mode tabs use "2h 30m", no "min") doubles as the readiness signal (see readiness-ladder capsule).

## Flow / Invariant
1. Anchor extraction at ONE stable leaf (duration), then derive spatial context (card → distance) by bounded ancestor walk.
2. Exclude interactive-control text from content parsing (radio-ancestor check).
3. Per-mode scope switching must be reflected at BOTH readiness and extraction or the two disagree.

## Probe (direct tests)
gmaps smoke test pins real semantics live: Austin→Houston driving returns min+miles+resolved waypoint "Austin, Texas"; transit London→Paris returns "2 hr 18 min"; driving must NOT leak transit time. Deterministic probe at pin: `grep -c "durRe" skills/gmaps/scripts/gmaps` → 4 (readiness + poll + extract share the grammar).

## Retrieve
grep-first (`EXTRACT_EXPR`, `durRe`, `distRe`, `Starting point`).

## Verdict
ADOPT anchor-leaf + ancestor-card scoping for any multi-result panel UI.

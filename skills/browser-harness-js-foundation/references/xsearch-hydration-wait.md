<!-- capsule-v2 -->
# XSearch Hydration Wait — fixed sleep, scroll batches, unquoted-attribute selectors

## Source
Repo: browser-harness-js @ main`6b18940` (unchanged vs base_sha).

## Question
How does xsearch extract tweets from a React-hydrated timeline, and which choices are load-bearing?

## Path / Symbol
`skills/xsearch/scripts/xsearch` :50-56 (networkIdle arm+wait), :59-61 (hydration sleep), :63-71 (scroll batch), :73-80 (extraction expr + selector note).

## Signature
```js
await ready;                                   // networkIdle DOES fire for x.com search pages
await new Promise(r => setTimeout(r, 4000));   // "Wait for React hydration and tweet rendering"
if (count > 6) {                               // ~6 tweets render in the initial batch
  const scrolls = Math.ceil((count - 6) / 3); // ~3 tweets per scroll batch
  ... window.scrollTo(0, document.body.scrollHeight) ... 1500ms settle ...
}
// Extraction: [data-testid=tweet] (unquoted attribute value — valid CSS — avoids escaped
// quotes inside the outer single-quoted JS string; no backticks anywhere in this heredoc).
// Per tweet: tweetText innerText, time[datetime], User-Name links → [author, handle, url]
// by POSITION (nameLinks[0]/[1]/[2]).
```

## Data Shape
`{author, handle, text, url, time}` where time is the raw `datetime` attribute (machine-readable ISO). Pretty output uses `\u00b7` escape rather than a literal '·' to stay ASCII-safe inside the heredoc.

## Decisive source
Selector comment :74-78: "CSS attribute values are unquoted — `[data-testid=tweet]` is valid CSS and selects the same nodes as `[data-testid=\"tweet\"]` — so no escaped quotes are needed inside the outer single-quoted JS string. (No backticks anywhere in this heredoc body: in an unquoted <<EOF, a lone backtick opens command substitution and trips an EOF parse error.)" The 4s hydration sleep is unconditional because x.com's timeline mounts after networkIdle with no reliable DOM signal short of polling `[data-testid=tweet]` presence (the simpler fixed-wait trade-off this script takes).

## Flow / Invariant
1. Event-based readiness + fixed hydration sleep is acceptable when extraction is tolerant of partial timelines.
2. Scroll math derives from measured initial-batch size (6) and per-scroll yield (3) — re-measure if the platform changes density.
3. data-testid attributes are X's stable contract — prefer them over visual classes.

## Probe (direct tests)
Deterministic probes at pin: `grep -c "data-testid=tweet" skills/xsearch/scripts/xsearch` → 2; `grep -c "4000" skills/xsearch/scripts/xsearch` → 1. Live run needs x.com egress (sandbox-blocked) — coverage caveat recorded.

## Retrieve
grep-first (`data-testid`, `scrollTo`).

## Verdict
ADOPT as the minimal viable timeline scraper; note it deliberately trades gmaps-style adaptive polling for simplicity.

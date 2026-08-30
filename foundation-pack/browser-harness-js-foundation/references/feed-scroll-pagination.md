<!-- capsule-v2 -->
# Feed-Scroll Pagination Ladder — scroll-to-bottom with no-growth stop

## Source
Repo: browser-harness-js @ main`6b18940` (unchanged vs base_sha).

## Question
How do the search skills load more than one viewport of results (Maps feed, X timeline) without infinite scrolling?

## Path / Symbol
- gmaps feed scroll :178-189.
- xsearch scroll batch :60-71.

## Signature
```js
// gmaps: scroll THE FEED container (not window) — div[role=feed] — and dispatch a
// bubbling scroll event so the app's lazy-loader notices:
const SCROLL_EXPR = `(function(){ var f=document.querySelector("div[role=feed]");
  if(!f) return; f.scrollTop=f.scrollHeight;
  f.dispatchEvent(new Event("scroll",{bubbles:true})); })()`
// Stop: i<25 cap AND prev<count AND two consecutive no-growth scrolls ("stable>=2").
// "The feed renders ~7 cards up front; more stream in as the feed is scrolled to its bottom."
// 700ms settle per scroll.

// xsearch: fixed-batch variant — ~6 tweets render initially; scrolls = ceil((count-6)/3),
// scrollTo(0, document.body.scrollHeight), 1500ms settle. Window-level because X scrolls the document.
```

## Data Shape
Progress metric differs by surface: Maps counts `a[href*='/maps/place/']` nodes (same selector as extraction → count IS progress); X just waits fixed time per batch and slices at extraction.

## Decisive source
gmaps :177-179 comment: "Scroll the feed to load up to `count`. The feed renders ~7 cards up front; more stream in as the feed is scrolled to its bottom. Stop at count, after two consecutive no-growth scrolls, or after a 25-scroll cap." The three-way stop (target reached / plateaued / capped) prevents both under-delivery and runaway loops when the feed recycles DOM nodes. Dedup at extraction (`seen[r.url]`) tolerates re-rendered duplicates from feed virtualization.

## Flow / Invariant
1. Scroll the actual scrollable container; synthesize the event the framework listens for.
2. Always pair a target condition with a plateau detector AND a hard cap.
3. Re-extract everything after scrolling and dedupe — don't accumulate partial extractions.

## Probe (direct tests)
gmaps smoke test exercises count>viewport live (`run --json "coffee shops in Austin TX" 3` plus a 20-result documented case in SKILL.md: "20 (scrolls the feed)"). Deterministic probes at pin: `grep -n "role=feed" skills/gmaps/scripts/gmaps` → 1 line (:184 SCROLL_EXPR); `grep -c "scrollHeight" skills/xsearch/scripts/xsearch` → 1 — ERRATUM pass-5 execution audit: shipped as "role=feed → 3"; live count at unchanged pin `main@6b189406` is 1 line (an earlier draft of this erratum claimed a second hit at ":16" — that is this capsule's own doc-comment line number, not repo source; the post-patch byte-exact re-execution battery caught it. Counts are re-derived against source and executed before trusting.)

## Retrieve
grep-first (`role=feed`, `scrollTop`, `stable`).

## Verdict
ADOPT the three-way stop as the default lazy-load pagination contract.

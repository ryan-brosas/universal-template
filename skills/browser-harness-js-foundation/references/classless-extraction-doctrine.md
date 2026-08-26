<!-- capsule-v2 -->
# Classless Extraction Doctrine — stable signals only, never Google class names

## Source
Repo: browser-harness-js @ main`6b18940` (unchanged vs base_sha).

## Question
How are Google results (Maps cards, news cards) parsed so obfuscated-class rotation can't break the extractor?

## Path / Symbol
- `skills/gmaps/scripts/gmaps` EXTRACT_EXPR comment :186-198 + parseResult :199-231.
- `skills/gnews/scripts/gnews` selector comment :100-112 + extraction IIFE :113-135.

## Signature
```js
// gmaps: one Runtime.evaluate extracts every card. Stable signals ONLY.
name    = link.getAttribute('aria-label')
rating  = first leaf token matching /^\d+\.\d$/ with length<=4      // leaf = childless text node, DFS walk
reviews = first leaf matching /^([\d,]+)$/
price   = first $-prefixed leaf; category = the leaf right after it (unless it's '·')
address = first leaf starting with a street number /^\d{1,5}[-A-Za-z]*\s/ that isn't the name
hours   = /^(Open|Closed|Open 24 hours|Temporarily closed)$/ leaf (+ optional '· Closes …' following leaf)
lat/lng = href match /!3d(-?\d+(?:\.\d+)?)!4d(-?\d+(?:\.\d+)?)/     // exact coords, NOT the @viewport
place_id= href /!19s(ChIJ[A-Za-z0-9_-]+)/ else /!1s(0x[0-9a-f]+:0x[0-9a-f]+)/
dedupe  = by href URL, insertion order preserved

// gnews: keep anchors that contain a div[role=heading] AND point off-Google
cards = [...document.querySelectorAll('a[href]')].filter(a =>
  a.querySelector('div[role=heading]') && !/^(www\.)?google\./.test(new URL(a.href).hostname));
// innerText line grammar: source \n title \n [snippet] \n '.' \n time — the standalone '.'
// line separates snippet from relative time and is absent when there is no snippet.
```

## Data Shape
gmaps result: `{name,rating,review_count,price,category,address,hours,lat,lng,place_id,url}`; gnews: `{title,url,source,snippet,time}`. Both produced inside ONE `Runtime.evaluate` returning a JSON string (`returnByValue:true`) — no per-element CDP round-trips.

## Decisive source
gmaps :187-190: "Stable signals ONLY — **Google's class names are obfuscated and rotate**, so the parser never keys off them." The leaf-token heuristics each carry a fallback chain (place_id tries ChIJ… then 0x..:0x..). gnews :101-105: "Selectors are class-agnostic: keep anchors that contain a role=heading and whose href is off-Google, so obfuscated Google class churn can't break extraction," plus the innerText line grammar including the sentinel '.' line. Contrast: xsearch/gsearch DO use fixed selectors (`[data-testid=tweet]`, `.tF2Cxc`, `.VwiC3b`) because those platforms expose stable test IDs / long-lived classes — the doctrine is per-site, not universal.

## Flow / Invariant
1. Never key extraction off rotated/compressed class names on Google surfaces; aria-labels, roles, href token grammar, and text-shape grammars are the durable surface.
2. Parse coordinates from the `!3d!4d` href tokens, never from `@lat,lng` (that's the viewport region — gmaps resolvePlace :398-401 makes the same distinction).
3. Extract everything in a single in-page pass; return JSON.stringify'd strings across CDP.

## Probe (direct tests)
gmaps smoke test asserts structured fields parse (`"place_id":"`, `"lat":`, maps/place url) AND that no unparsed placeholder leaks (`refuse "__GMAPS_"`). Deterministic probes at pin: `grep -n 'role=heading' skills/gnews/scripts/gnews` → 4 lines (:77–78 comments, :86 filter, :88 title read); `grep -o "aria-label" skills/gmaps/scripts/gmaps | wc -l` → 12 occurrences on 10 lines (:276 and :368 carry two each; singles at :197 comment, :206 result-name getAttribute read, :263/:317/:349 `[aria-label="Directions"]` panel scopes, :274/:293/:301 radio-tab census comments+exprs) — ERRATUM pass-5 execution audit: shipped as "→ 2 / ≥4"; heading count was comment-line contamination and aria-label is one-per-line at unchanged pin `main@6b189406` (counts re-derived against source; occurrence-exact is authoritative).

## Retrieve
grep-first (`EXTRACT_EXPR`, `parseResult`); graph covers SDK plane only for this repo.

## Verdict
ADOPT for any Google-surface scraper; keep the per-site exception note so porters don't "fix" xsearch into classlessness unnecessarily.

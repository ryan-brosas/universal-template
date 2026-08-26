<!-- capsule-v2 -->
# Bot-Interstitial Sniffing — fail fast with recovery instructions, never wait out the wall

## Source
Repo: browser-harness-js @ main`6b18940` (unchanged vs base_sha).

## Question
How do the downloaders and searchers detect anti-bot walls, and what do they tell the caller?

## Path / Symbol
- ytdl player-ready poll :146-155 (YouTube unusual-traffic regex + error text).
- ttdl player-ready poll :199-206 ("verify|robot|human|captcha|something went wrong|unusual|slide to|puzzle" over first 200 chars of body innerText).
- gmaps readiness failure :171-174 (consent-wall message); JSON bail-fast in findata/gsearch (`v.ct !== "application/json"` → immediate throw with head excerpt).

## Signature
```js
const body = document.body ? document.body.innerText.slice(0,200) : '';
const bot = /verify|robot|human|captcha|something went wrong|unusual|slide to|puzzle/i.test(body);
if (s.bot) throw new Error('TikTok is showing a "verify you are human" / captcha interstitial —
  back off and retry later, or open the URL once in the browser to clear it.');
// ytdl twin: /unusual traffic|Our systems have detected|Are you a robot|not a robot/i
```

## Data Shape
Sniff runs on every poll tick BEFORE the ready check so a wall shortens the wait instead of stretching it; diagnostics carry page state for the error: ytdl includes the page title in "player did not become ready... page title", findata/gsearch include `content-type` + first 120–160 chars of the body head.

## Decisive source
The error strings themselves are the contract: each names the remedy — back off, retry later, or "open the URL manually once in the browser to clear it" (ytdl) — turning a dead end into a recoverable operator action. rsearch's variant is structural rather than textual: the FIRST search.json call returning non-JSON is treated as the anti-bot cookie-seeding step and retried (:190-194) instead of surfacing an error. gmaps distinguishes consent wall from no-results in its readiness timeout message ("the page may have hit a consent/cookie wall, or the query matched nothing. Open the URL in the browser once to check.").

## Flow / Invariant
1. Sniff cheaply and early (innerText prefix + regex), classify, and fail with instructions.
2. Distinguish "wall" (retryable, human-fixable) from "empty" (legitimate zero results) in messages.
3. When the platform's own response seeds the bypass (Reddit 403 cookies), retry before reporting.

## Probe (direct tests)
Deterministic probes at pin: `grep -c "Are you a robot" skills/ytdl/scripts/ytdl` → 1; `grep -o "captcha" skills/ttdl/scripts/ttdl | wc -l` → 3 occurrences on 3 lines (:226 comment, :234 poll regex, :238 thrown error message) — ERRATUM pass-5 execution audit: shipped as `grep -c → 2`, live count at unchanged pin `main@6b189406` is 3 (line-based `grep -c` reports LINES and still misses multi-mention lines; occurrence-exact is authoritative). Live interstitial reproduction not possible sandboxed (no Google/TikTok egress) — coverage caveat recorded; regexes pinned verbatim.

## Retrieve
grep-first (`interstitial`, `unusual traffic`, `consent`).

## Verdict
ADOPT the sniff-classify-instruct triad; keep the Reddit-style structural exception separate from textual walls.

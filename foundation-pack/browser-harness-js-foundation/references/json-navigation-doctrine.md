<!-- capsule-v2 -->
# JSON Navigation Doctrine — JSON pages fire no lifecycle events

## Source
Repo: browser-harness-js @ main`6b18940` (unchanged vs base_sha). Cross-validated live in Chrome/151 headless during this pass.

## Question
How do you fetch a JSON endpoint through the browser (for cookies/UA/bot-bypass) when Chrome emits no readiness events for `application/json` navigations?

## Path / Symbol
- `skills/cdp/docs/../interaction-skills/json-navigation.md` (the documented doctrine; gsearch `follow --json` cites it).
- Strategy 1 — poll-innerText: `gsearch follow` JSON branch (scripts/gsearch :71-95), `findata navAndPoll` (:139-158), SEC companyfacts projection expr.
- Strategy 2 — frameNavigated + same-origin fetch: `findata navJsonFetch` (:160-186), Yahoo chart expr :193.

## Signature
```js
// Strategy 1: poll until innerText parses as JSON
await cdp(sid,'Page.navigate',{url});
while (Date.now()-start < 15000) {
  const v = eval('JSON.stringify({ready: parses(document.body.innerText), ct: document.contentType, ...})');
  if (v.ready) return v.value;
  if (v.ct && /text\/html/i.test(v.ct) && v.len>0) throw new Error('non-JSON response: '+v.head); // bail fast
  await sleep(80);
}
// Strategy 2: wait commit, then fetch the URL from inside its own page
session.onEvent((m,p,sid)=>{ if (m==='Page.frameNavigated' && p.frame.url!=='about:blank') committed=true; });
await cdp(sid,'Page.navigate',{url});
// then in-page: fetch(window.location.href) → raw body text, skip viewer render entirely
```

## Data Shape
Strategy 1's poll expression does readiness AND projection in ONE shot ("so the (multi-MB) body is parsed exactly once, when ready" — findata comment). Both strategies bound CDP evals with a node-side `Promise.race` timeout because "CDP calls have no built-in timeout" (rsearch :216-218, findata :176-178).

## Decisive source
- gsearch :73-76: "application/json navigations fire NO Page lifecycle events (networkIdle never fires), and Chrome's JSON viewer renders the body into the DOM on its own schedule — so poll document.body.innerText until JSON.parse succeeds rather than waiting on a lifecycle event. Reading innerText once at a fixed time gives '' or a partial/truncated blob... **the poll IS the head validation**. Bail early if the response is actually HTML (error page / login wall / anti-bot challenge)."
- findata SKILL.md "How it works" quantifies the choice with measurements: small bodies (~0.3s prices) favor strategy 2 because the viewer render is pure overhead; the 3.7MB companyfacts favors polling because by the time innerText is ready Chrome's viewer has already parsed the body, making the page-side `JSON.parse` nearly free (~16ms vs ~800ms cold fetch+parse). Also records that `Network.getResponseBody` at loadingFinished would be fastest but "crashes the harness's WebSocket on multi-MB bodies."
- rsearch variant for SPAs: don't even wait for full load — wait only for `Page.frameNavigated` matching the origin regex (`^https:\/\/([^/]*\.)?reddit\.com\/`, main-frame only via `!p.frame.parentId`) then poll `document.readyState !== 'loading'`; "the fetch only needs the committed origin, not a fully-built page."

## Flow / Invariant
1. HTML pages: arm `Page.setLifecycleEventsEnabled:true` + `waitFor(networkIdle)` BEFORE navigate. JSON pages: lifecycle events NEVER come — switch doctrine.
2. Poll cadences are tuned per body size (80ms JSON polls; rsearch 100ms readyState; gmaps 200ms feed).
3. A non-JSON content-type with non-empty body is an immediate error, never a timeout — fail fast on walls/challenges.

## Probe (direct tests)
LIVE BEHAVIORAL CONFIRMATION this pass: against headless Chromium 151 (`chromium --headless=new --remote-debugging-port=9333`), navigating a tab to a JSON URL produced no `load`/`networkIdle` lifecycle event while `document.body.innerText` became parseable — matching the documented doctrine (probe transcript in work record). Static probe: `grep -c "lifecycleEvent" skills/gsearch/scripts/gsearch` → 2 (arm+wait on the HTML path only).

## Retrieve
`search_graph --project browser-harness-js --query "navJsonFetch"` (entry-point surface lists session-level symbols; findata helpers are heredoc-inline, grep-first).

## Verdict
ADOPT both strategies + the size-based selection rule; the "poll IS the head validation" phrasing is the invariant to preserve.

<!-- capsule-v2 -->
# Request capture → in-page replay — how do you learn a site's internal API from its own traffic and then call it as the page?

**Source:** browser-harness-js MIT `main@6b189406`; Codebase Memory `browser-harness-js`. **Question:** When the UI path is gated or exposes too little data, what is the capture-then-replay contract that reads an endpoint out of the Network panel and re-calls it with the page's own credentials?

## Capture requestWillBeSent, fetch omitted POST bodies, replay via Runtime.evaluate with filtered headers, vary the URL, or rewrite in flight with Fetch
**Path/Symbol:** `skills/cdp/interaction-skills/reverse-engineer-api.md` (whole doc, 110L: capture :7-37, replay :39-59, vary :61-77, intercept :79-95, traps :103-110); wrappers confirmed live: `generated.getRequestPostData @ generated.ts:14853`, `Fetch.continueRequest @ generated.ts:14735` (search_graph this pass).
**Signature:** capture = `session.onEvent((m,p) => … 'Network.requestWillBeSent' …)` filtered by an URL regex; POST body = `session.Network.getRequestPostData({ requestId })` when `p.request.hasPostData` is true and `postData` is absent; replay = `(async () => fetch(url, {method, headers, body?, credentials:'include'}))()` evaluated with `{awaitPromise:true, returnByValue:true}`.
**Data Shape:** captured record `{url, method, headers, postData?, hasPostData, requestId}`; replay result `{status, body}`.

### Decisive source
```js
const seen = []; const off = session.onEvent((method, p) => {
  if (method === 'Network.requestWillBeSent' && /\/api\/search/.test(p.request.url))
    seen.push({ url: p.request.url, method: p.request.method, headers: p.request.headers, postData: p.request.postData, hasPostData: p.request.hasPostData, requestId: p.requestId });
});
// POST bodies are often MISSING from the event: if (cap.postData == null && cap.hasPostData)
const { postData } = await session.Network.getRequestPostData({ requestId: cap.requestId });
// replay IN THE PAGE so cookies/origin/referer match the site's own call:
const expr = `(async () => { const r = await fetch(${JSON.stringify(cap.url)}, {
  method: ${JSON.stringify(cap.method)},
  headers: ${JSON.stringify(Object.fromEntries(Object.entries(cap.headers).filter(([k]) =>
    /^(authorization|x-|csrf|content-type|accept)/i.test(k))))},
  ${cap.postData ? `body: ${JSON.stringify(cap.postData)},` : ''}
  credentials: 'include', })
  return { status: r.status, body: await r.text() } })()`
```

**Flow:** enable Network BEFORE the trigger (arm-before-act) → predicate-filter `requestWillBeSent` into a small capture list (Network.enable is verbose; never buffer every subresource) → complete POST bodies via `getRequestPostData` when `hasPostData` → read the contract off `{url, method, headers, postData}` (auth header, CSRF token, body shape) → rebuild the call INSIDE `Runtime.evaluate` so it runs as the page (`credentials:'include'`; cookies/Content-Type/Referer are auto-added by the page, only Authorization/CSRF/custom headers must be re-supplied — hence the filter regex) → vary/paginate by string-editing the URL with polite pacing (~400ms) → alternative with no UI trigger: `Fetch.enable({patterns:[{urlPattern, requestStage:'Request'}]})` + `Fetch.continueRequest({requestId, url})` mutates the page's own request in flight.
**Invariant:** (1) REPLAY FROM THE PAGE, NOT FROM NODE — a fetch via `Runtime.evaluate` carries the site's cookies, origin, referer and TLS fingerprint; the identical call from Node with copied cookies gets flagged/blocked. (2) Captured auth/CSRF tokens are one-shot or short-lived: RE-CAPTURE fresh tokens before each replay session, never hardcode. (3) `credentials:'include'` is mandatory or the in-page fetch ships no cookies. (4) Header re-supply is a FILTER, not a copy: forwarding the page's auto-added headers can corrupt or leak them; forward only `/^(authorization|x-|csrf|content-type|accept)/i`. (5) This is the same trust boundary as the page's own call — use it to work WITH a site's API, not to bypass access controls or rate limits. Relationship: `same-origin-authenticated-fetch` covers authentication-by-navigation before a same-origin call; THIS seam covers learning an unknown endpoint from observed traffic and re-parameterizing it.
**Probe:** doctrine doc — no direct unit test. Deterministic probes: wrapper existence pinned by search_graph retrievals above (`getRequestPostData` generated.ts:14853, `continueRequest` generated.ts:14735); doc section anchors `grep -n "## Capture the request\|## Replay in-page\|## Traps" skills/cdp/interaction-skills/reverse-engineer-api.md` (:7, :39, :103). Live-replay behavior needs egress+credentials; recorded caveat per pass-3 doctrine pattern.
**Coverage caveat:** check_index_coverage on the doc path: no_recorded_issue / metadata_match; prose symbols are not graph nodes — retrieval evidence is the two generated.ts wrappers plus direct whole-doc read.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-harness-js", query: "getRequestPostData", limit: 3, fields: ["signature", "name", "file"] });
// resolves browser-harness-js.skills.cdp.sdk.generated.getRequestPostData @ generated.ts:14853  (executed this pass)
```

## Verdict
Adopt capture→replay-from-page as the standard move whenever UI driving is the obstacle but the endpoint is legitimately reachable — including `getRequestPostData` for event-omitted bodies and the header filter. Adapt the politeness pacing and the sensitive-header list to your target. Omit the Fetch.intercept branch only if you never need to mutate requests without a UI trigger.

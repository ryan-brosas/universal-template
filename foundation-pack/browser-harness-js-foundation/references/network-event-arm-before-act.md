<!-- capsule-v2 -->
# network-event-arm-before-act — why do Network waits miss their events, and what are the per-target scoping rules?

**Source:** browser-harness-js MIT `main@6b1894061e7a09a65a974d7d65a210b9a7ef06e0`; Codebase Memory `browser-harness-js`. **Question:** How do you wait on a request/response reliably and read its body without a silent miss?

## Arm-first event contract
**Path/Symbol:** `skills/cdp/interaction-skills/network-requests.md` whole doc — watching (:5–22), waitFor (:24–37), response body (:39–57), post bodies (:55–57), Fetch interception/mocking (:59–86), SPA success signal (:88–102), Traps (:104–109).
**Signature:** `session.Network.enable({})` → `session.waitFor('Network.responseReceived', p => url-test, timeout)` → `Network.getResponseBody({requestId: ev.requestId})`; mock: `Fetch.enable({patterns:[{urlPattern, requestStage}]})` + fulfillRequest/continueRequest/failRequest.
**Data Shape:** bodies available only transiently — read immediately after loadingFinished; redirects/cached/discarded throw. Small request bodies ride `params.request.postData`; large ones need `Network.getRequestPostData`. waitFor REJECTS on timeout (never returns null).

### Decisive source
```md
- **`Network.enable` must be called before the request fires.** If you enable
  after the click, you'll miss the event. Enable once at session start and
  leave it.
- **`Network.enable` is per-target.** After `session.use(iframe.targetId)`,
  call `Network.enable({})` again inside that target.
- **Request IDs are unique per target, not global.**
```

**Flow:** enable FIRST (arm-before-act; cheapest SPA "did it work?" signal = click → waitFor responseReceived 200) → filter by URL/status predicate → getResponseBody by requestId from THE SAME target → Fetch domain only when intercepting (it disables the HTTP cache for matched URLs — disable when done).
**Invariant:** Three scoping laws: arm-before-act (events before enable don't exist), per-target enable (each session.use target needs its own), per-target requestIds (crossing targets silently mismatches). The rejection-vs-null asymmetry decides error handling shape.
**Probe:** `grep -cF 'Enable once at session start' skills/cdp/interaction-skills/network-requests.md` → 1; `grep -cF 'is per-target.' <same>` → 1; `grep -cF 'unique per target' <same>` → 1; `grep -cF 'reject on timeout' <same>` → 1; `grep -cF 'Network.loadingFinished' <same>` → 1; `grep -cF 'disables the HTTP cache' <same>` → 1.
**Retrieve:** search_graph --project browser-harness-js --query "getResponseBody" resolves the generated.ts wrapper line-exact.

## Verdict
Adopt arm-first + per-target scoping as non-negotiable CDP hygiene. Adapt predicate/timeout budgets per flow. Omit Fetch mocking details if you never intercept.

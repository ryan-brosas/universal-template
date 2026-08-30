<!-- capsule-v2 -->
# SDK resolve endpoint — OS-intercepted clicks still count, but only after the same safety gate

**Source:** LinkForty core AGPL-3.0-only `main@8919b1ecdc48f8c53340c4590b5f0eae0680abf8`; Codebase Memory `ext-core`. **Question:** When the OS intercepts a short link (UL/App Link) before the server can 302, how does the mobile SDK get the payload AND keep attribution intact?

## GET /api/sdk/v1/resolve/:shortCode[/:templateSlug]
**Path/Symbol:** `src/routes/sdk.ts:handleResolve` (:459-695), routes :697-705; probe instantiation :453-457 with the incident comment :433-452.
**Signature:** Response `{ shortCode, linkId, deepLinkPath?, appScheme?, iosUrl?, androidUrl?, webUrl?, utmParameters?, customParameters?, clickedAt }`.
**Data Shape:** Same Redis keys as redirect (`link:<code>` / `link:<template>:<code>`, TTL 300) → the two endpoints share one cache population; optional `fp_*` query params feed fingerprint storage like the redirect path.

### Decisive source
```ts
// sdk.ts:524-546 — why resolve enforces block but honors warn:
// Without this, a link whose owner is restricted still resolved here — and
// this endpoint hands back the destination and deep-link data directly,
// which is precisely the information the redirect refuses to disclose. ...
// A `warn` outcome deliberately still resolves. The interstitial is a browser
// affordance an app cannot render ...
if (safety === 'block') {
  // Same response as an unknown short code, and no click recorded.
  return reply.status(404).send({ error: 'Link not found' });
}
```

**Flow:** lookup (cache → SQL with shared SELECT fragment) → safety gate (`block` ⇒ anonymous 404; `warn` resolves because apps cannot render interstitials and warn is suspicion-not-confirmation) → setImmediate async writer inserts click (RETURNING id variant — no pre-generated id needed since nothing synchronous consumes it), stores fingerprint, emits real-time event with `redirectReason: 'sdk_resolve'` + empty redirectUrl, fires click webhooks → JSON response returns deep-link data.
**Invariant:** Any endpoint that RESOLVES a code must enforce the SAME block gate as the redirect — the redirect's confidentiality guarantee is only as strong as the weakest resolving path; both paths must select identical columns because they share one cache key (owner_suspension capsule).
**Probe:** `bash -c "grep -cF \"redirectReason: 'sdk_resolve'\" src/routes/sdk.ts"` → 1 (:634); direct tests `src/routes/sdk-cache-bypass.test.ts`: it('the SDK endpoint itself refuses to resolve a restricted link'), it('still blocks after an SDK resolve has primed the same cache key').

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-core", query: "sdk resolve shortCode deep link data", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt a non-redirecting resolve twin for OS-intercepted links with identical gating; adapt response fields; omit click re-recording if your SDK flow already attributes via install reporting instead.

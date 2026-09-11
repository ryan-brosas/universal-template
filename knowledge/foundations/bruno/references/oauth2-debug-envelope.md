<!-- capsule-v2 -->
# Token-request debug envelope — every OAuth2 attempt returns request/response evidence, even on failure

**Source:** bruno MIT `main@675965612ff11b23bc9b6c9541110a287bcb2967`; Codebase Memory `ext-bruno`. **Question:** How does the desktop client give users full visibility into token requests (which usually happen invisibly before the "real" request) — including failures?

## Connected graph-selected seam
**Path/Symbol:** `packages/bruno-electron/src/utils/oauth2.js:getCredentialsFromTokenUrl` (:53-137); consumers append `requestDetails` into `debugInfo.data` in each grant function.
**Signature:** `getCredentialsFromTokenUrl({requestConfig, certsAndProxyConfig}) → {credentials, requestDetails}`.
**Data Shape:** `requestDetails = {requestId: Date.now().toString(), fromCache: false, completed: true, request: {url, headers, data, method}, response: {url, headers, data, status, statusText, timeline, error?, timestamp?}, requests: []}` — deliberately shaped like a MAIN request so the UI's network timeline renders it identically.

### Decisive source
```js
} else if (error?.code) {
  // error.config is not available here
  const { url: requestUrl, headers: requestHeaders, data: requestData } = requestConfig;
  requestDetails = {
    request: { url: requestUrl, headers: requestHeaders, data: requestData },
    response: {
      status: '-',
      statusText: error?.code,           // e.g. ENOTFOUND / ECONNREFUSED as statusText
      headers: {},
      data: safeStringifyJSON(error?.errors),
      timeline: error?.timeline
    }
  };
}
```

**Flow:** send via `makeAxiosInstance({proxyMode, proxyConfig, httpsAgentRequestFields, interpolationOptions})` (token requests honor the SAME proxy/TLS config as the parent request) → success ⇒ parse arraybuffer→JSON, capture both sides → HTTP error (`error.response`) ⇒ record real status + parsed body → transport error (`error.code`, no response) ⇒ synthesize an entry with `status:'-'` and the errno code as statusText, reusing `error.timeline` if the timeline agent attached one → grant fn pushes into `debugInfo.data` and persists credentials only when non-error; refresh flow clears stored credentials on any failure and returns nulls WITHOUT throwing.
**Invariant:** failures produce EVIDENCE, never silence — the three-branch capture must keep all three shapes renderable by the same viewer; `responseType:'arraybuffer'` on every token call so binary/odd content types can't throw pre-parse; credentials persist only after parse succeeds.
**Probe:** no dedicated spec for getCredentialsFromTokenUrl (coverage caveat recorded); grant-level behavior pinned via `packages/bruno-tests/src/auth/oauth2/*` integration flows.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-bruno", query: "getCredentialsFromTokenUrl requestDetails debugInfo", limit: 5 });
```

## Verdict
Adopt evidence-always-return + main-request-shaped entries + three-branch capture. Adapt to your telemetry plane; omit Bruno's requestId scheme. Coverage caveat: no direct unit spec — verified against whole-file source read.

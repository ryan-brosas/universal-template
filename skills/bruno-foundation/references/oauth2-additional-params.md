<!-- capsule-v2 -->
# Additional-parameters injection — enabled-gated header/query/body routing for token requests

**Source:** bruno MIT `main@675965612ff11b23bc9b6c9541110a287bcb2967`; Codebase Memory `ext-bruno`. **Question:** How do you let users attach arbitrary extra params to OAuth2 token/refresh/authorize requests — routed per-slot (headers vs queryparams vs body) without breaking the form-urlencoded contract?

## Connected graph-selected seam
**Path/Symbol:** `packages/bruno-requests/src/auth/oauth2-helper.ts:applyAdditionalParameters` (:69-98); electron twin `packages/bruno-electron/src/utils/oauth2.js` (:745+); authorize-side query-only variant inside `getOAuth2AuthorizationCode`.
**Signature:** `applyAdditionalParameters(requestConfig, data, params: AdditionalParameter[] = [])`.
**Data Shape:** `AdditionalParameter = {name, value, enabled, sendIn: 'headers'|'queryparams'|'body'}`; slots: `additionalParameters.token` / `.refresh` / `.authorization` select which request the array feeds.

### Decisive source
```ts
params.forEach((param) => {
  if (!param.enabled || !param.name) return;          // gate FIRST
  switch (param.sendIn) {
    case 'headers':  requestConfig.headers[param.name] = param.value || ''; break;
    case 'queryparams':
      try {
        const url = new URL(requestConfig.url);
        url.searchParams.append(param.name, param.value || '');
        requestConfig.url = url.href;
      } catch (error) { throw new Error(`Invalid token URL: ${requestConfig.url}`); }
      break;
    case 'body':     data[param.name] = param.value || ''; break;
  }
});
```

**Flow:** skip disabled/nameless params → route by sendIn: headers set directly (empty value allowed as ''); queryparams REPARSE the URL and append (never string-concat — existing query must survive); body writes into the plain object BEFORE `qs.stringify`, preserving application/x-www-form-urlencoded. Authorization slot is query/headers only (`getAdditionalHeaders` builds headers; query appended during URL construction) — never body, since GET-like authorize navigations have none.
**Invariant:** body mutation happens pre-stringify (post-stringify keys silently vanish); URL reparse-and-append keeps prior params intact; empty-string values are legitimate and distinct from disabled; helper throws a NAMED error on unparseable token URLs rather than corrupting the request.
**Probe:** `packages/bruno-requests/src/auth/oauth2-helper.spec.ts` grant suites exercise parameter plumbing alongside placement pins (:87-281 client-credentials basic-vs-body).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-bruno", query: "applyAdditionalParameters additionalParameters", limit: 5 });
```

## Verdict
Adopt enabled-first gating + three-slot routing + pre-stringify body mutation + URL-reparse appends. Adapt slot names to your config schema; omit Bruno's UI-facing defaults. Coverage caveat: none — clean coverage at pin.

<!-- capsule-v2 -->
# Dual-region provider-registration twins — how do you register two regional variants of one provider without duplicating logic?

**Source:** pi-bailian MIT `main@c26c4e9855c87b18b17d5717b8c9171a27031d06`; Codebase Memory `pi-bailian`. **Question:** What is shared and what differs between the intl/CN registrations, and how does the env-var key reference work?

## Registration-twin seam
**Path/Symbol:** `src/index.ts` default export (:156-184) with constants `BAILIAN_INTL_BASE_URL` (:18), `BAILIAN_CN_BASE_URL` (:24), `API_KEY_ENV` (:30), `PROVIDER_ID_INTL`/`PROVIDER_ID_CN` (:35-36).
**Signature:** `export default function (pi: ExtensionAPI)` → two `pi.registerProvider(id, {baseUrl, apiKey, api, models, oauth})` calls.
**Data Shape:** both providers share ONE `apiKey: "$BAILIAN_CODING_PLAN_API_KEY"` literal-$ env reference, one `api: "anthropic-messages"`, and identical `oauth.getApiKey`/`oauth.refreshToken` handlers; they differ in id, baseUrl, catalog, and login wrapper.

### Decisive source
```ts
  pi.registerProvider(PROVIDER_ID_INTL, {
    baseUrl: BAILIAN_INTL_BASE_URL,
    apiKey: API_KEY_ENV,
    api: "anthropic-messages",
    models: bailianModels,
    oauth: {
      name: "Alibaba Bailian Coding Plan (International)",
      login: loginBailian,
      refreshToken: refreshBailianToken,
      getApiKey: getApiKey,
    },
  });
  ...
  // Register China region provider with OAuth-style login
  pi.registerProvider(PROVIDER_ID_CN, {
    baseUrl: BAILIAN_CN_BASE_URL,
    apiKey: API_KEY_ENV,
    api: "anthropic-messages",
    models: bailianModelsCN,
    oauth: {
      name: "Alibaba Bailian Coding Plan (China)",
      login: loginBailianCN,
      refreshToken: refreshBailianToken,
      getApiKey: getApiKey,
    },
  });
```

The extension's own doc comment states the region-as-id usage contract (:150-153):
```ts
 * Usage:
 * - Environment variable: export BAILIAN_CODING_PLAN_API_KEY=sk-sp-xxxxx
 * - Interactive login: /login bailian-coding-plan
```

**Flow:** one extension entry registers BOTH regions back-to-back; region selection becomes a host-level choice of provider id (`bailian-coding-plan` vs `bailian-coding-plan-cn`) rather than a config field; the CN login wrapper delegates to the shared implementation with `"cn"` (:113-115).
**Invariant:** the env-var string is the SAME for both twins — one exported variable serves either region, so users never re-export per region. Handler objects are shared references, not copies; only display-facing fields diverge.
**Probe:** `test/models.test.ts:128-157` pins the twin invariant at catalog level (same ids, same properties, `(CN)` name suffix); registration body itself has NO dedicated upstream test — recorded caveat, evidence is direct source read :156-184 (full CN block :171-183 verified line-by-line this pass; both calls share the identical `API_KEY_ENV` and handler references).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-bailian", query: "bailian provider extension coding plan register", limit: 5, fields: ["signature", "lines"] });
```
Executed live at pin: total 7, first page returned all five named functions (`loginBailian`, `loginBailianCN`, `refreshBailianToken`, `validateApiKey`, `getApiKey`), has_more true; page 2 returned the test-local validator + a Branch node. Retrieval CAVEAT observed at this pin: query "register provider models baseUrl extension default export" returns total **0** — the registration seam lives in the unnamed default export, which BM25 cannot address by function name; retrieve it via this vocabulary or read `src/index.ts:156-184` directly.

## Verdict
Adopt twin registration with shared handlers + shared env-var reference and region-as-provider-id naming (`<id>` / `<id>-cn`). Adapt ids, URLs, and catalogs to your vendor. Omit any per-region credential logic — none exists here by design.

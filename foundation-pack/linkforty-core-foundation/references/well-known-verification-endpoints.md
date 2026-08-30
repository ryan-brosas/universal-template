<!-- capsule-v2 -->
# Well-known verification endpoints — env-configured AASA + assetlinks.json for Universal/App Links

**Source:** LinkForty core AGPL-3.0-only `main@8919b1ecdc48f8c53340c4590b5f0eae0680abf8`; Codebase Memory `ext-core`. **Question:** What must a deep-link server serve at /.well-known/ for OS-level link verification, and what are the serving constraints?

## wellKnownRoutes — apple-app-site-association + assetlinks.json
**Path/Symbol:** `src/routes/well-known.ts:wellKnownRoutes` (:15-104).
**Signature:** `GET /.well-known/apple-app-site-association` and `GET /.well-known/assetlinks.json`, both built from env at request time.
**Data Shape:** Env inputs: `IOS_TEAM_ID` + `IOS_BUNDLE_ID`; `ANDROID_PACKAGE_NAME` + `ANDROID_SHA256_FINGERPRINTS` (comma-separated, trimmed, Boolean-filtered). Missing config ⇒ 404 with actionable message + docs URL; empty fingerprint list ⇒ 500 with an example value.

### Decisive source
```ts
// well-known.ts:35-45 + :89-98 — the exact OS-verified shapes:
const aasa = { applinks: { apps: [], details: [
  { appID: `${teamId}.${bundleId}`, paths: ['*'] } ] } };
const assetlinks = [{ relation: ['delegate_permission/common.handle_all_urls'],
  target: { namespace: 'android_app', package_name: packageName,
            sha256_cert_fingerprints: fingerprints } }];
// :47-50 — serving constraints:
// 1. Without .json extension  2. With application/json content-type
// 3. Over HTTPS (in production)
```

**Flow:** iOS fetches AASA (no extension!) over HTTPS to verify the appID `TEAMID.BUNDLE` against associated-domains entitlement → Android fetches assetlinks.json matching package_name + SHA-256 cert fingerprints → `paths: ['*']` claims every path on the domain, which is exactly why in-app browsers bypassing UL need the web-fallback reorder elsewhere (redirect capsule).
**Invariant:** The AASA route must NOT carry a `.json` suffix while still sending `application/json`; multi-fingerprint support exists because debug+release certs differ; both endpoints fail loudly-but-safely (4xx/5xx JSON) rather than serving malformed verification files.
**Probe:** `bash -c "grep -cF 'delegate_permission/common.handle_all_urls' src/routes/well-known.ts"` → 1 (:91); direct tests: none target this file — recorded honest caveat; shape pinned by Apple/Google doc references in-file (:17-19, :56-59).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-core", query: "apple-app-site-association assetlinks well-known", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the endpoint shapes + serving constraints verbatim when hosting verified links; adapt path scoping (`paths`) and fingerprint management; omit if your links are not app-claim domains.

<!-- capsule-v2 -->
# Admin API key JWT verification — how does a kid-addressed token authenticate without a lookup secret?

**Source:** Ghost MIT `main@81292b004cf59591f03d7dbe01f28f31c09ee813`; Codebase Memory `ext-ghost`. **Question:** What is the exact verification order and option set for Admin-API `Authorization: Ghost <jwt>` tokens?

## apiKeyAuthenticateWithToken
**Path/Symbol:** `ghost/core/core/server/services/auth/api-key/admin.js:apiKeyAuthenticateWithToken` (:112–221; defaults :19–23; header extraction :30–46).
**Signature:** `async (originalUrl: string, token: string, ignoreMaxAge?: boolean): Promise<{ user, apiKey }>`.
**Data Shape:** JWT_OPTIONS_DEFAULTS = `{algorithms: ['HS256'], maxAge: '5m'}`; kid = JWT header key id; ApiKey.secret stored hex; audience regex built from URL path.
### Decisive source
```js
const decoded = jwt.decode(token, { complete: true });   // UNVERIFIED decode just to read kid
const apiKeyId = decoded.header.kid;
const apiKey = await models.ApiKey.findOne({ id: apiKeyId }, { withRelated: ['integration'] });
if (apiKey.get('type') !== 'admin') throw new errors.UnauthorizedError({ code: 'INVALID_API_KEY_TYPE' });
// limit funnel for custom/builtin integrations ...
const secret = Buffer.from(apiKey.get('secret'), 'hex');
let options = Object.assign({ audience: new RegExp(`/?${version}/${api}/?$`) }, jwtValidationOptions);
try { jwt.verify(token, secret, options); } catch (err) { throw new errors.UnauthorizedError({ code: 'INVALID_JWT', ... }); }
```
**Flow:** unverified decode → require kid → load ApiKey BY ID (secret never leaves the DB) → type must be 'admin' → plan-limit gate blocks non-internal integrations when over limit → verify with pinned algorithm list + maxAge 5m (omitted when ignoreMaxAge) + audience regex from `legacyApiPathMatch(originalUrl)` → optional user attach when api_key has user_id.
**Invariant:** (1) Algorithm is PINNED to HS256 (`algorithms: ['HS256']`) — no alg confusion. (2) The DB round-trip happens BEFORE verification; an unknown kid fails as UNKNOWN_ADMIN_API_KEY rather than a signature error. (3) Secret must be hex-decoded to bytes or HMAC mismatches. (4) Audience binds the token to ONE API surface via `req.originalUrl` (post version-rewrite), so a content-API token can't be replayed against admin even with a valid signature.
**Probe:** `grep -cF "algorithms: ['HS256']" ghost/core/core/server/services/auth/api-key/admin.js` → expect `1`; `grep -cF "maxAge: '5m'" ghost/core/core/server/services/auth/api-key/admin.js` → expect `1`; `grep -cF "decoded.header.kid" ghost/core/core/server/services/auth/api-key/admin.js` → expect `1`; direct tests: `grep -cF "should NOT authenticate known+valid versioned API key with a token created for non-versioned API'" ghost/core/test/unit/server/services/auth/api-key/admin.test.js` → expect `1`; `grep -cF "\"shouldn't authenticate with JWT signed > 5min ago\"" ghost/core/test/unit/server/services/auth/api-key/admin.test.js` → expect `1`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ghost", query: "apiKeyAuthenticateWithToken admin api key", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt kid→DB-key→pinned-alg→audience-regex verification order wholesale. Adapt storage/lookup to host ORM; keep hex-decode only if secrets are hex-stored.

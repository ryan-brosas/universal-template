<!-- capsule-v2 -->
# Dynamic client registration credential grammar — which clients get secrets, when do they expire, and why must stores never delete them?

**Source:** typescript-sdk MIT `main@3924de9`; Codebase Memory `mnt-hdd-utopia-inspo-mcp-typescript-sdk`. **Question:** How does a registration endpoint decide secret generation and expiry, and what contract do the handlers expect from client stores?

## Registration handler & store contract
**Path/Symbol:** `packages/server-legacy/src/auth/handlers/register.ts`: options (:15-41), `DEFAULT_CLIENT_SECRET_EXPIRY_SECONDS = 30*24*60*60` (:43), handler (:45-124); store interface `packages/server-legacy/src/auth/clients.ts` (:6-21).
**Signature:** `clientRegistrationHandler({ clientsStore, clientSecretExpirySeconds = 30d, rateLimit, clientIdGeneration = true })`; throws at construction when `!clientsStore.registerClient`.
**Data Shape:** public client ⇔ `token_endpoint_auth_method === 'none'`; response `{...metadata, client_secret?, client_secret_expires_at?, client_id?, client_id_issued_at?}` as 201 JSON.

### Decisive source
```ts
// :88-97
const isPublicClient = clientMetadata.token_endpoint_auth_method === 'none';
// Generate client credentials
const clientSecret = isPublicClient ? undefined : crypto.randomBytes(32).toString('hex');
const clientIdIssuedAt = Math.floor(Date.now() / 1000);
const clientsDoExpire = clientSecretExpirySeconds > 0;
const secretExpiryTime = clientsDoExpire ? clientIdIssuedAt + clientSecretExpirySeconds : 0;
const clientSecretExpiresAt = isPublicClient ? undefined : secretExpiryTime;
```
```ts
// clients.ts :15 NOTE (the invariant in prose)
// NOTE: Implementations should NOT delete expired client secrets in-place. Auth middleware
// provided by this library will automatically check the `client_secret_expires_at` field…
```

**Flow:** metadata schema-validated (`InvalidClientMetadataError`) → secret/expiry derived → optional UUID id generation (`clientIdGeneration=false` leaves `client_id` unset for stores that mint their own) → `clientsStore.registerClient(clientInfo)` whose RETURNED value is what ships — a store may override/enforce fields → 201. Rate limit is deliberately stricter: 20 requests/HOUR vs 50/15min elsewhere ("registration endpoints are particularly sensitive to abuse").

**Invariant:** expiry is DATA, not deletion: the check lives in `authenticateClient` (`client.client_secret_expires_at < now` → 'Client secret has expired'), so a store that prunes rows breaks token refreshes for still-valid access tokens issued to that client; `expiresAt=0` means never-expiring (opt-in via `clientSecretExpirySeconds=0`, documented as not-recommended). Public clients NEVER carry `client_secret_expires_at` even with expiry configured — absence of the field is how middleware distinguishes "no secret" from "expired".

**Probe (direct tests):** `packages/server-legacy/test/auth/handlers/register.test.ts` — :30 'throws error if client store does not support registration', :129 'sets client_secret to undefined for token_endpoint_auth_method=none', :142 'sets client_secret_expires_at for public clients only', :192 'sets no expiry when clientSecretExpirySeconds=0', :212 'sets no client_id when clientIdGeneration=false'; clientAuth.test.ts :105 expired-secret rejection.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-mcp-typescript-sdk", query: "clientRegistrationHandler registerClient clientSecretExpiry", limit: 3 });
```

## Verdict
Adopt the public-client ⇒ no-secret/no-expiry derivation and expiry-as-data; adapt secret entropy and id generation to your crypto stack; omit CORS-any on the registration route if you have no browser-native registrants.

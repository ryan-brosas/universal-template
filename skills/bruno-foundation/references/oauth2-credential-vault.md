<!-- capsule-v2 -->
# OAuth2 credentials vault — encrypted per-collection token storage with session-scoped browser partitions

**Source:** bruno MIT `main@675965612ff11b23bc9b6c9541110a287bcb2967`; Codebase Memory `ext-bruno`. **Question:** Where does a desktop API client keep OAuth2 tokens between runs, and how do you keep concurrent users' authorize windows from sharing cookies?

## Connected graph-selected seam
**Path/Symbol:** `packages/bruno-electron/src/store/oauth2.js:Oauth2Store` (whole 186L); consumers in `packages/bruno-electron/src/utils/oauth2.js` (`persistOauth2Credentials`, `getStoredOauth2Credentials`).
**Signature:** `getCredentialsForCollection({collectionUid, url, credentialsId}) → decrypted object | null`; `updateCredentialsForCollection({..., credentials = {}})`.
**Data Shape:** electron-store JSON file `oauth2`: `{collections: [{collectionUid, sessionId?, credentials?: [{url, data: <encrypted string>, credentialsId}]}]}`. Credentials values are `encryptStringSafe(safeStringifyJSON(credentials))`; reads `decryptStringSafe` + `safeParseJSON`.

### Decisive source
```js
updateCredentialsForCollection({ collectionUid, url, credentialsId, credentials = {} }) {
  const encryptionResult = encryptStringSafe(safeStringifyJSON(credentials));
  const encryptedCredentialsData = encryptionResult.value;
  ...
  let filteredCredentials = oauth2DataForCollection?.credentials?.filter((c) => (c?.url !== url) || (c?.credentialsId !== credentialsId));
  if (!filteredCredentials) filteredCredentials = [];
  filteredCredentials.push({ url, data: encryptedCredentialsData, credentialsId });
```

**Flow:** upsert-by-filter-and-push keyed `(collectionUid)` outer, `(url, credentialsId)` inner — the filter predicate uses OR (`c.url !== url || c.credentialsId !== credentialsId`) to REMOVE all others for that pair, then push replaces. `getSessionIdOfCollection` lazily mints a uuid sessionId per collection (create-if-missing inside the getter). `clearSessionIdOfCollection` deletes BOTH `sessionId` and `credentials`. Every accessor wraps try/catch and logs rather than throws — a corrupt secrets file degrades to cache-miss.
**Invariant:** tokens are NEVER stored plaintext on disk (encryption at rest is the port-critical half); one sessionId per collection drives an Electron `partition:` so each authorize BrowserWindow gets isolated cookie space; the OR-shaped filter must stay OR — rewriting it as AND silently duplicates credential rows.
**Probe:** no dedicated upstream spec file for this store (electron store tests cover preferences/system-proxy only) — coverage caveat recorded; behavior pinned indirectly via `packages/bruno-tests/src/auth/oauth2/*` flow tests.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-bruno", query: "Oauth2Store updateCredentialsForCollection", limit: 5 });
```

## Verdict
Adopt at-rest encryption + `(scope, url, credentialsId)` triple-keying + lazy session-id minting. Adapt electron-store/Electron partitions to your platform's secure storage; omit the specific file layout. Coverage caveat: no direct unit spec for Oauth2Store itself.

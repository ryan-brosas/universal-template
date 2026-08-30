<!-- capsule-v2 -->
# OAuth2 authorize-window state machine — redirect interception, fail-closed state validation, and the protocol-handler twin

**Source:** bruno MIT `main@675965612ff11b23bc9b6c9541110a287bcb2967`; Codebase Memory `ext-bruno`. **Question:** How does an embedded-browser OAuth2 authorization flow detect its callback reliably, reject forged callbacks, and clean up every listener when the window dies?

## Connected graph-selected seam
**Path/Symbol:** `packages/bruno-electron/src/ipc/network/authorize-user-in-window.js:authorizeUserInWindow` (:15-263, `matchesCallbackUrl` :5); twin `packages/bruno-electron/src/utils/oauth2-protocol-handler.js:handleOauth2ProtocolUrl` (:46-132).
**Signature:** `authorizeUserInWindow({authorizeUrl, callbackUrl, session, additionalHeaders = {}, grantType = 'authorization_code', expectedState}) → Promise<{authorizationCode, debugInfo} | {implicitTokens, debugInfo}>`.
**Data Shape:** module-singleton `oauth2AuthorizationRequest = {resolve, reject, debugInfo, expectedState, timestamp}` for the system-browser path; `debugInfo.data` accumulates request/response snapshots by object reference (handlers mutate the SAME `currentMainRequest` pushed at `onBeforeRequest`).

### Decisive source
```js
const matchesCallbackUrl = (url, callbackUrl) => {
  if (!url) return false;
  // Match the callback URL and require an OAuth2 response indicator
  // (code query params for authorization code flow, or hash fragment for implicit flow).
  // This prevents false matches on intermediate pages (e.g. /auth/login) when the
  // callback URL is a root path like https://hostname/.
  return url.href.startsWith(callbackUrl.href)
    && (url.searchParams.has('code') || url.hash.length > 1);
};
```

**Flow:** close all non-main windows → new hidden BrowserWindow with `partition: session` → cert-error handler honors the app's TLS-verify preference (fail-closed unless user disabled) → webRequest observers record per-mainFrame debug snapshots (`did-start-navigation` RESETS `currentMainRequest` to null on each new main-frame nav) → `did-navigate`/`will-redirect` feed `onWindowRedirect`: OAuth `error` param rejects FIRST (descriptive error beats null code), then callback match sets `finalUrl` + closes window → in the `close` handler (after listener teardown): validate `state` — missing expected or mismatched ⇒ reject "OAuth2 state mismatch" FAIL-CLOSED — then split by grantType: implicit parses the URL HASH fragment via URLSearchParams; code flow reads `code` query param. Window closed without finalUrl ⇒ reject 'Authorization window closed'. `ERR_ABORTED` from loadURL is swallowed (redirect artifact), other errors reject+close.
**Invariant:** state validation happens AFTER window close but BEFORE any token/code is trusted; error-param check precedes callback matching so `?error=` on a callback-shaped URL still rejects; all five webRequest listeners plus webContents listeners are nulled in the `close` handler or they leak per flow. Protocol-handler twin mirrors the same ladder for `bruno://` deep links and REJECTS any previously-pending request when a new one registers (single-slot pending promise).
**Probe:** no direct spec file for either file (coverage caveat recorded); behavior pinned end-to-end by `packages/bruno-tests/src/auth/oauth2/authorizationCode.js` flow tests incl. `generateCodeChallenge` (:20-25).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-bruno", query: "handleOauth2ProtocolUrl expectedState", limit: 5 });
// resolves packages/bruno-electron/src/utils/oauth2-protocol-handler.js :46-132
```

## Verdict
Adopt: response-indicator-gated prefix matching, error-before-match ordering, post-close fail-closed state validation, single-slot pending-request arbitration, exhaustive listener teardown. Adapt BrowserWindow/webRequest plumbing; omit usebruno callback defaults. Coverage caveat: no unit spec — verified against source read + upstream integration tests.

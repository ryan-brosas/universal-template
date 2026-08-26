<!-- capsule-v2 -->
# Session token & tab identity — how do you resume a recording session across tabs/reloads while keeping per-tab isolation and project binding?

**Source:** OpenReplay AGPL-3.0 `main@99eb60032f70906f6887195c400f173c00a08522`; Codebase Memory `openreplay`. **Question:** Where do sessionToken, pageNo, and tabId live so a session survives reloads but not other projects — and what is the cross-tab stitch format?

## Session getSessionToken / incPageNo / getTabId / applySessionHash
**Path/Symbol:** `tracker/tracker/src/main/app/session.ts:getSessionToken` (:115-127), `incPageNo` (:104-113), `getTabId` (:162-180), `applySessionHash` (:138-151), `tokenSeparator` (:13).
**Signature:** `getSessionToken(projectKey?: string): string | undefined`; `setSessionToken(token, projectKey)`; `applySessionHash(hash: string)`.
**Data Shape:** sessionStorage keys `session_token_key` (`token$_$projectKey` composite), `session_pageno_key`, `session_tabid_key`; `tokenSeparator = '_$_'`; in-memory `this.token` mirrors storage.

### Decisive source
```ts
const tokenWithProject = this.token || this.app.sessionStorage.getItem(this.options.session_token_key)
if (projectKey && tokenWithProject) {
  const savedProject = tokenWithProject.split(tokenSeparator)[1]
  if (!savedProject || savedProject !== projectKey) {
    this.app.sessionStorage.removeItem(this.options.session_token_key)   // wrong project → wipe
    this.token = undefined
    return undefined
  }
}
const token = tokenWithProject ? tokenWithProject.split(tokenSeparator)[0] : null
```
```ts
applySessionHash(hash: string): void {          // "pageNo&token" URL-stitch format
  const hashParts = decodeURI(hash).split('&')
  let token = hash
  let pageNoStr = '100500'                      // back-compat sentinel for bare tokens
  if (hashParts.length == 2) { [pageNoStr, token] = hashParts }
```

**Flow:** every start reads the stored composite → projectKey mismatch DELETES the stored token (a tracker moved between projects must never resume the old session) → new sessions mint via server and store `token$_$projectKey` → each page-load `incPageNo()` bumps a persistent counter (becomes BatchMetadata.pageNo) → `tabId` is a random 12-char id persisted in sessionStorage so all tabs of one browser share it but different browsers don't → `getSessionHash()`/`applySessionHash()` encode/decode `pageNo&token` for URL-based session stitching across agents/devices.
**Invariant:** The `_$_` separator is load-bearing: tokens are opaque server strings that could contain most characters, so the split index [1] must be the LAST field. Session continuation is opt-in per project — passing a projectKey is what makes stale-token reuse SAFE. The magic `'100500'` default page number exists purely for legacy hash formats that carried no pageNo; do not "fix" it to 0.
**Probe:** `grep -n "tokenSeparator" tracker/tracker/src/main/app/session.ts | head -2` from repo root → lines 13 and 118 (verified live); `grep -n '100500' tracker/tracker/src/main/app/session.ts` → line 141. Direct tests: `npx jest src/tests/session.unit.test.ts` in `tracker/tracker` → 16/16 green.
**Retrieve:** search_graph project openreplay query "Session getSessionToken tokenSeparator projectKey" → rank-1 `Session.getSessionToken :115-127` line-exact at pin.

## Verdict
Adopt composite-token-with-project-binding + persistent pageNo/tabId storage + `pageNo&token` stitch format as pure identity behavior; adapt sessionStorage abstraction to your storage layer; omit the specific random-id generator if your stack has a canonical uuid helper.

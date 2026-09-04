<!-- capsule-v2 -->
# Cookie jar wrapper — `__Host-` prefix discipline and the tough-cookie callback/promise duality trap

**Source:** bruno MIT `main@675965612ff11b23bc9b6c9541110a287bcb2967`; Codebase Memory `ext-bruno`. **Question:** How do you wrap a shared cookie jar so scripts can read/write cookies safely — preserving `__Host-` semantics, Infinity expiry, and not hanging on callback-style calls?

## Connected graph-selected seam
**Path/Symbol:** `packages/bruno-requests/src/cookies/index.ts:cookieJarWrapper` (:186-530); jar plumbing `addCookieToJar` (:13), `getCookieStringForUrl` (:27), `hasHostPrefix` (:11), `createCookieObj` (:107), `saveCookies` (:173).
**Signature:** `jar() → {getCookie(url,name,cb?), hasCookie(...), getCookies(url,cb?), setCookie(url,nameOrObj,value?,cb?), setCookies(url,arr,cb?), deleteCookie(url,name,cb?), deleteCookies(url,cb?), clear(cb?)}`.
**Data Shape:** ONE module-singleton `CookieJar` for the whole app; every wrapper method is dual-mode (callback optional ⇒ promise).

### Decisive source
```ts
// __Host- prefixed cookies must have hostOnly=true per the cookie spec.
// tough-cookie only sets hostOnly=true when domain is derived from the URL,
// so we must not set domain explicitly for these cookies.
const hasHostPrefix = (cookieName: string): boolean => cookieName.startsWith('__Host-');
...
const defaults = hasHostPrefix(obj.key) ? {} : { domain: new URL(url).hostname };
```

**Flow (setCookie):** normalize `name→key` alias → host-prefixed names get EMPTY defaults (domain derived from URL at set time ⇒ hostOnly) while normal names get explicit `domain: hostname` → `createCookieObj` coerces invalid expiry strings to `Infinity` and stamps creation/lastAccessed → `setCookieSync(ignoreError:true)` (malformed sets never crash a request). Read path: `getCookiesSync(url, {secure: isPotentiallyTrustworthyOrigin(url)})`, filter `expires > Date.now()`, join `'; '`. Delete: fetch matching cookies, prefer exact-path match else first (tough-cookie pre-sorts by path-length desc), remove by `(domain,path,key)` triple.
**Invariant:** THE TRAP — in callback mode you must NOT return tough-cookie's promise: with a callback provided, `cookieJar.getCookies()` returns a NEVER-RESOLVING promise, so `await` on a returned value hangs forever (pinned by spec section "Callback mode does not return a Promise"); `saveCookies` handles both array AND single-string `set-cookie` headers; `parseCookieString` maps string `'Infinity'`/`Infinity` → null for UI display.
**Probe:** `packages/bruno-requests/src/cookies/index.spec.ts` :9+ — pins basic ops, multi-cookie ops, deletion paths, hasCookie, the callback-not-a-Promise contract, and error handling.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-bruno", query: "hasHostPrefix cookieJarWrapper __Host-", limit: 5 });
```

## Verdict
Adopt singleton-jar + dual-mode wrapper, `__Host-` no-explicit-domain rule, ignoreError set semantics, expired-filtering on read. Adapt to your cookie lib's API; omit Bruno's moment-based coercion if your dates are already typed. Coverage caveat: none — clean coverage at pin.

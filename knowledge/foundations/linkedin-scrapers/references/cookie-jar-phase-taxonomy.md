<!-- capsule-v2 -->
# Cookie-jar phase taxonomy — which cookies does LinkedIn hand out per auth phase, and how do you parse a `set-cookie` array into a jar safely?

**Source:** linkedin-private-api MIT `master@e083f37`; Codebase Memory `linkedin-private-api`. **Question:** Which cookie names exist per auth phase (anonymous vs authenticated vs user-supplied), and what parsing kernel turns axios `set-cookie` arrays into that jar?

## Three jar shapes and the first-key-wins parse kernel
**Path/Symbol:** `src/types/anonymous-cookies.ts` (:1–8), `src/types/auth-cookies.ts` (:1–13), `src/core/login.ts:parseCookies` (:12–19) + `userPass` (:93–124) + `userCookie` (:126–149).
**Signature:** `<T>(cookies: string[]): Partial<T>` — reduce over raw `set-cookie` strings, `parseCookie` from the `cookie` pkg, `pickBy((v,k) => k === Object.keys(parsedCookie)[0])`, lodash `merge` accumulate.
**Data Shape:** `AnonymousCookies` = REQUIRED `bcookie, bscookie, JSESSIONID, lang, lidc, lissc`; `AuthCookies` = ALL-OPTIONAL superset adding `chp_token, li_at, liap, lidc, lissc, recent_history, wwepo`. The runtime cache jar is looser than both types: `{JSESSIONID, authenticated}` (what mockLogin's `set-cookie: ['JSESSIONID=…', 'authenticated=true']` actually produces).

### Decisive source
```ts
// src/core/login.ts:12-19
const parseCookies = <T>(cookies: string[]): Partial<T> =>
  cookies.reduce((res, c) => {
    let parsedCookie = parseCookie(c);
    parsedCookie = pickBy(parsedCookie, (v, k) => k === Object.keys(parsedCookie)[0]);
    return merge(res, parsedCookie);
  }, {});
// userPass: anonymous GET → sessionId = parseCookies<AnonymousCookies>(headers['set-cookie']).JSESSIONID!
//           POST authenticateUser → parsedCookies = parseCookies<AuthCookies>(set-cookie)
//           fs.writeFile(SESSIONS_PATH, JSON.stringify({ ...cachedSessions, [username]: parsedCookies }))  // un-awaited
// setRequestHeaders (:28): cookieStr = reduce(cookies, (res,v,k) => `${res}${k}="${v}"; `, '')
```

**Flow:** anonymous GET `/uas/authenticate` → its `set-cookie` carries ONLY the bootstrap jar (`JSESSIONID` with the `ajax:` prefix intact; `bcookie/lidc/lissc…` are the anonymous-phase names this phase issues) → sessionId feeds the form-encoded credential POST → the auth response's `set-cookie` array is parsed into the authenticated jar → spread-merged into `sessions.json` under the username key (preserving sibling accounts) → serialized as `k="v"; ` pairs + `csrf-token` = verbatim `JSESSIONID`. `userCookie` accepts a partial jar (`{JSESSIONID}` alone is enough — spec-pinned :152/:156), stores it verbatim when a username is given, and `useCache:false` skips the read-through.
**Invariant:** each `set-cookie` string parses to a multi-key object (`name, path, expires…`) but only the FIRST key is the cookie — `pickBy(k === Object.keys(...)[0])` drops the attribute tail; skipping it poisons the jar with `path:'/'` entries. The merge accumulator must be lodash `merge` (deep) so per-cookie objects combine across the array. The two type surfaces are DOCUMENTATION of wire phases, not runtime validators — nothing enforces required-vs-optional at parse time; porters should keep the typed phases as docs but expect the live jar to be whatever `set-cookie` delivered. Cookie VALUES are wrapped in literal double quotes in the header (see dual-persona-auth-headers).
**Probe:** direct tests pin the whole ladder in `test/login/login.spec.ts`: header merge shape `cookie: 'JSESSIONID="ajax:4458204165719552435"; authenticated="true"; '` + `'csrf-token': <same sessionId>` (:38–39, asserted 3× across userPass/userCookie suites), cache-write payload `{username: {JSESSIONID, authenticated}}` (:40–57), cached-login short-circuit with ZERO axios calls (`verify(axios.get(), { ignoreExtraArgs: true, times: 0 })` at :80 and :196 — once per suite), `userCookie` partial-jar accept (:152–157) and cache-store verify (:163–170), `useCache:false` bypass (:217–222); fixture `test/utils/mockLogin.ts` shows exactly which set-cookie arrays each phase returns.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linkedin-private-api", query: "parseCookies pickBy cookies reduce merge", limit: 5 });
// rank#1 login.parseCookies Function src/core/login.ts 12-19; twins AnonymousCookies/AuthCookies Interfaces resolve too
```

## Verdict
Adopt the phase-typed cookie jars as documentation plus the first-key-wins parse kernel for any multi-set-cookie harvest; adapt jar member lists to current LinkedIn responses (names rot; the KERNEL is the durable part); omit none of the attribute-dropping — keeping parsed cookie options as values corrupts both the header string and the csrf token derivation. Coverage: check_index_coverage stdin-JSON on login.ts + cited paths `no_recorded_issue`+`metadata_match` @ gen 2026-08-23T00:12:08Z; graph anchor resolves line-exact rank#1. Companion to `dual-persona-auth-headers` (header personas) and `sessions-json-cache` (cache file mechanics) — THIS capsule owns the set-cookie→jar parsing step and the phase vocabulary those capsules assume.

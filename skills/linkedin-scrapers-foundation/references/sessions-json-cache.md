<!-- capsule-v2 -->
# Sessions.json cache — multi-account credential cache with read-through-create and useCache opt-out (how do I persist per-user API sessions without re-login storms)?

**Source:** linkedin-private-api MIT `master@e083f37`; Codebase Memory `linkedin-private-api`. **Question:** What is the minimal durable shape for caching authenticated sessions for MULTIPLE accounts in one process, with an escape hatch to force fresh login?

## The login cache
**Path/Symbol:** `src/core/login.ts:readCacheFile/tryCacheLogin/userPass/userCookie` (:38–134).
**Signature:** `readCacheFile(): Promise<Record<string, AuthCookies>>` keyed by username; `tryCacheLogin({ useCache = true, cachedSessions, username })` returns boolean; both `userPass({username, password?, useCache})` and `userCookie({username?, cookies: {JSESSIONID, li_at?}, useCache})` return the live `Client`.
**Data Shape:** `sessions.json` in `process.cwd()` — flat `{ [username]: { JSESSIONID, authenticated } }`. No TTL, no encryption (porters should add both).

### Decisive source
```ts
private async readCacheFile(): Promise<Record<string, AuthCookies>> {
  let cachedSessions: Record<string, AuthCookies>;
  try {
    const sessionsBuffer = (await fs.readFile(SESSIONS_PATH).catch(() => fs.writeFile(SESSIONS_PATH, '{}'))) || '{}';
    cachedSessions = JSON.parse(sessionsBuffer.toString());
  } catch (err) { cachedSessions = {}; }
  return cachedSessions;
}
// userPass: if (this.tryCacheLogin(...)) return this.client;
//           if (!password) throw new TypeError('password is required for login');
```

**Flow:** READ (missing file ⇒ create it empty via `.catch(() => fs.writeFile(SESSIONS_PATH, '{}'))`, corrupt JSON ⇒ `{}`) → CACHE HIT when `useCache !== false` AND username provided AND jar exists ⇒ set headers, return client with ZERO network calls. MISS ⇒ password required (loud `TypeError`, not a silent retry) ⇒ anonymous-seed → authenticate → MERGE-write `{...cachedSessions, [username]: parsedCookies}` so other accounts' entries survive. `userCookie` is the manual-jar twin: caller-supplied cookies bypass the network entirely and are cached only if `username` was given.
**Invariant:** cache is checked BEFORE any credential use; the write preserves sibling entries (spread-merge, never blind overwrite); `useCache:false` forces fresh auth but still rewrites the jar. Known gaps recorded for porters: the two `fs.writeFile` persistence calls (:105, :130) are un-awaited fire-and-forget, and stale jars are trusted until an API call fails (no validation hook).
**Probe:** `test/login/login.spec.ts` — :43–55 write-after-login (`writeFile(sessions.json, JSON.stringify({username: cachedCookies}))`), :57–82 cache hit makes ZERO axios get/post calls (`verify(axios.get(), {times: 0})`), :84–108 `useCache:false` re-authenticates despite a cached jar, :110–119 missing file auto-created as `'{}'`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linkedin-private-api", query: "userPass tryCacheLogin sessions.json", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: username-keyed JSON jar + read-through-create + spread-merge writes + loud missing-password error. Adapt: add atomic writes (tmp+rename), TTL/expiry checks, and env-var path override before production — the upstream file is deliberately naive. Contrast in-suite: EasyApplyJobsBot's per-day cookie files (cookie-session-persistence) are single-account; THIS design is the multi-account reference. Direct tests pin all four branches.

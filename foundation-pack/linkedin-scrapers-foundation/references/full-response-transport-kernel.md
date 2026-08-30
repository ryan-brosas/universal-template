<!-- capsule-v2 -->
# Full-response-flagged transport kernel — one axios instance serves header-hungry auth calls AND data-only API calls over base-relative endpoints (how do I keep a single transport when one call needs headers and every other needs only the body?)

**Source:** linkedin-private-api MIT `master@e083f37` (`e083f370c331ed643348158b8c64f905de477626`); Codebase Memory `linkedin-private-api`. **Question:** How does a cookie-authenticated API client stay ONE transport for login (must read `set-cookie`) and voyager reads (want parsed bodies), while every endpoint string stays a bare relative path?

## The dual-return kernel under every request
**Path/Symbol:** `src/core/request.ts:Request` (:16–50) + `buildUrl` (:7); sole `fullResponse: true` callers: `src/requests/auth.request.ts:getAnonymousAuth` (:15) + `authenticateUser` (:33–36).
**Signature:** `get<T>(url, reqConfig?: {fullResponse?: boolean} & AxiosRequestConfig): Promise<T | AxiosResponse<T>>` (mirror overload pair on `post`); `setHeaders(headers: Record<string,string>): void`; `const buildUrl = (url: string) => new URL(url, linkedinApiUrl).toString()`.
**Data Shape:** instance created ONCE as `axios.create({ paramsSerializer, withCredentials: true, ...(proxy && { proxy }) })`; default return is `response.data`, `{fullResponse: true}` flips the SAME method to the whole `AxiosResponse`. `Client({proxy})` threads one optional `AxiosProxyConfig` down Client→LinkedInRequest→Request.

### Decisive source
```ts
const buildUrl = (url: string) => new URL(url, linkedinApiUrl).toString();
// ...
constructor({ proxy }: RequestOpts = {}) {
  this.request = axios.create({ paramsSerializer, withCredentials: true, ...(proxy && { proxy }) });
}
setHeaders(headers: Record<string, string>): void {
  this.request.defaults.headers = headers;              // WHOLESALE replacement — no merge
}
// get AND post share the same tail on both overloads:
const response = await this.request.get<T>(buildUrl(url), reqConfig);
return reqConfig?.fullResponse ? response : response.data;
```

**Flow:** domain requests pass slash-less relative paths (`'search/blended'`, `'me'`,
`'growth/normInvitations'`, ``\`messaging/conversations/\${id}\```) → buildUrl resolves them against
`https://www.linkedin.com/voyager/api/` → exactly TWO calls need headers (the anonymous auth GET and
the credential POST) and pass `{fullResponse: true}` so Login can read `headers['set-cookie']`;
every other caller omits the flag and gets parsed bodies. Persona switches ASSIGN
`defaults.headers` wholesale (`{...requestHeaders, cookie, 'csrf-token'}` replaces the object).
**Invariant:** endpoint strings MUST stay slash-less — with WHATWG URL semantics,
`new URL('/me', 'https://host/voyager/api/')` yields `https://host/me`, silently discarding the
`/voyager/api` base path (a leading slash means root-relative); `fullResponse` is the ONLY sanctioned
route to headers; `setHeaders` is total replacement so each persona swap must spread the COMPLETE
header set or lose prior headers. Deliberately ABSENT: retry, timeout, backoff, error normalization —
raw axios errors reach repositories/callers; porters must add their own resilience ladder instead of
assuming one exists.
**Probe:** `test/login/login.spec.ts:29–41` pins the post-login transport state EXACTLY:
`expect(client.request.request.defaults.headers).toEqual({...requestHeaders, cookie: `JSESSIONID="ajax:…"; authenticated="true"; `, 'csrf-token': sessionId})` (cache-hit branch :57–82 pins zero wire calls);
`test/invitation/invitation-repository.spec.ts:17` rebuilds stub URLs as
`new URL('relationships/sentInvitationViewsV2', linkedinApiUrl).toString()` — tests mirror buildUrl
byte-for-byte so a base change breaks loudly. Runner caveat: jest config exists but this checkout has
NO installed node_modules — probe evidence here is source+spec text, not a live run.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linkedin-private-api", query: "buildUrl setHeaders fullResponse", limit: 6 });
// get_code_snippet: "linkedin-private-api.src.core.request.Request" → whole class :16–50
```

## Verdict
Adopt the single-instance dual-return kernel: flag-selected response granularity, base-relative
endpoint vocabulary, wholesale header-object swap for persona changes. Adapt the base URL, param
serializer, and proxy plumbing to your host. Omit nothing behavioral; ADD what upstream intentionally
lacks (retry/timeouts) in YOUR caller layer, never inside the kernel. Coverage caveat:
check_index_coverage = no_recorded_issue/metadata_match on src/core/request.ts and both test paths;
suite not executable in this checkout (runner block recorded in the lane work record).

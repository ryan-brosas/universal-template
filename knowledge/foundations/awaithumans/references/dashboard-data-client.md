<!-- capsule-v2 -->
# Dashboard data client — how does the bundled operator UI talk to the API it is served from, and recover when the dev API server moves?

**Source:** awaithumans (Apache-2.0) `main@bc05b8e7`; Codebase Memory `mnt-hdd-utopia-inspo-awaithumans`. **Question:** What base-URL resolution, retry, auth-cookie, and error-shaping contract must a same-origin dashboard fetch client preserve?

## apiFetch + discovery-cached base resolution
**Path/Symbol:** `packages/dashboard/lib/server/client.ts:apiFetch` (:123–162), `resolveApiBase` (:32–55), `buildApiError` (:103–121); thin per-domain wrappers in sibling `tasks.ts`/`audit.ts`.
**Signature:** `apiFetch<T>(path: string, options?: RequestInit): Promise<T>` — throws `UnauthorizedError` (401) or `ApiError{status, errorCode, docsUrl, message}`.
**Data Shape:** `BUNDLED_MODE` from `NEXT_PUBLIC_AWAITHUMANS_BUNDLED === "true"` at build time; module-level `cachedApiBase`/`cachedAt` with `CACHE_TTL_MS = 30_000`.

### Decisive source
```ts
async function resolveApiBase(forceRefresh = false): Promise<string> {
	// Bundled mode: same origin, always. No discovery, no cache needed.
	if (BUNDLED_MODE) return "";
	if (!forceRefresh && cachedApiBase && Date.now() - cachedAt < CACHE_TTL_MS)
		return cachedApiBase;
	try {
		const res = await fetch("/api/discover");
		if (res.ok) {
			const data = (await res.json()) as { url: string; source: string };
			cachedApiBase = data.url.replace(/\/$/, "");
			cachedAt = Date.now();
			return cachedApiBase;
		}
	} catch { /* Discovery route unreachable — fall through to default */ }
	cachedApiBase = DEFAULT_API_URL;
	cachedAt = Date.now();
	return cachedApiBase;
}
```
```ts
let res: Response;
try {
	res = await doFetch(base);
} catch {
	// Network error (server gone, port closed) — invalidate cache, rediscover, retry once
	invalidateCache();
	base = await resolveApiBase(true);
	res = await doFetch(base);
}
if (res.status === 401) throw new UnauthorizedError();
if (!res.ok) throw await buildApiError(res);
// 204 No Content and similar — caller isn't expecting a body.
if (res.status === 204 || res.headers.get("content-length") === "0") return undefined as T;
return res.json() as Promise<T>;
```

**Flow:** every dashboard call → resolve base (bundled ⇒ `""` same-origin; dev ⇒ 30 s-cached `/api/discover` answer → `DEFAULT_API_URL` fallback) → one fetch with `credentials:"include"` + JSON content-type → network-level failure invalidates the cache and retries discovery EXACTLY once → status dispatch.
**Invariant:** Bundled mode never discovers (same-origin "" keeps CSP `connect-src 'self'` true); the retry-once loop only fires on thrown network errors (server restarted on another port), never on HTTP error statuses; `.message` on ApiError is always banner-safe human text — taken from the server envelope `{error, message, docs}` (`service_error_handler` shape), falling back to FastAPI's `detail`, then a generic status string; 401 is a distinct class so callers can redirect to login; 204/empty-body resolves `undefined` instead of crashing `res.json()`.
**Probe:** No direct test exists under `lib/server/` at this pin (coverage caveat). Deterministic probes executed instead: source pins above byte-checked against the checkout; wrapper census read in `lib/server/tasks.ts` :8–61 (`claimTask` comment documents the 409→refresh-and-show-winner contract).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-awaithumans", query: "apiFetch dashboard server client", file_pattern: "*client.ts", limit: 10 });
// −31.87 apiFetch 123-162; −19.72 resolveApiBase 32-55; −19.72 buildApiError 103-121
```

## Verdict
Adopt the two-mode base resolution, retry-once-after-discovery-invalidation, and envelope-shaped error ladder; adapt `/api/discover` to your own discovery route or drop it if you are always same-origin; omit the Next.js-specific env flag plumbing. Distinct plane from managed-client-wire-contract.md (embed partner uploads) and sdk-client-facade.md (agent SDK) — three clients, three trust domains. Coverage caveat: no dedicated vitest suite for this file; vitest itself absent (no node_modules).

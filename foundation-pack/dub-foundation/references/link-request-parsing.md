<!-- capsule-v2 -->
# Short-link request parsing — how do you derive domain and multi-level key from a raw edge request (and what host/preview rewrites apply)?

**Source:** dub AGPL-3.0-or-later `main@873edc5a`; Codebase Memory `dub`. **Question:** Given only the incoming request, what are the canonical rules for extracting link domain, key, fullKey, and fullPath — including localhost/preview and unicode handling?

## parse() — single source of key/domain truth
**Path/Symbol:** `apps/web/lib/middleware/utils/parse.ts:parse` (4-41); consumers: root `apps/web/middleware.ts:36`, `LinkMiddleware` (`link.ts:41`), `getFinalUrl` Play-store branch.
**Signature:** `parse(req: NextRequest): {domain, path, fullPath, key, fullKey, shortLink, searchParamsObj, searchParamsString}`.
**Data Shape:** `domain` = Host header, www-stripped, lowercased; preview hosts collapse to `SHORT_DOMAIN` (with one special-case path mapping to a case-sensitive test domain); `key` = first path segment decoded; `fullKey` = entire path sans leading slash decoded.

### Decisive source
```ts
let domain = req.headers.get("host") as string;
let path = req.nextUrl.pathname;
domain = domain.replace(/^www./, "").toLowerCase();
if (domain === "dub.localhost:8888" || domain.endsWith(".vercel.app")) {
  if (path.toLowerCase() === "/case-sensitive-test") {
    domain = "dub-internal-test.com";        // special case for case-sensitive link test
  } else {
    domain = SHORT_DOMAIN;                   // dev + preview URLs share prod short domain
  }
}
const fullPath = `${path}${searchParams.length > 0 ? `?${searchParams}` : ""}`;
// decodeURIComponent to handle foreign languages like Hebrew and Korean
const key = decodeURIComponent(path.split("/")[1]);
const fullKey = decodeURIComponent(path.slice(1));
```

**Flow:** every entry into link logic starts here; downstream normalization is SEPARATE: `punyEncode(originalKey)` then lowercase unless the domain is case-sensitive (`isCaseSensitiveDomain`), empty key becomes `_root`, trailing `+` means inspect mode.
**Invariant:** `key` vs `fullKey` distinction is load-bearing — single-segment links use `key`, multi-level subpaths (e.g. `github/repo`) need `fullKey` for lookup while stats pages re-use `key`. Decoding happens BEFORE punycasing/lowercasing. The parse layer never throws on odd input: missing segments yield `""`/`undefined` which upstream converts to `_root`. Host-based routing decisions (app/api/admin/partners) are made from this same parsed domain — one parse per request, passed down.
**Probe:** no direct unit test upstream (coverage caveat). Deterministic probe: `dub.sh/stats/github` → `{domain:"dub.sh", key:"stats", fullKey:"stats/github", path:"/stats/github"}`; percent-encoded Korean key must survive decode; `.vercel.app` preview maps onto SHORT_DOMAIN.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "parse middleware domain fullKey shortLink", limit: 10 });
```

## Verdict
Adopt: one parse function owning domain/key/fullKey/fullPath derivation with explicit preview-host collapse and decode-before-normalize ordering; keep `_root` and inspect-suffix conventions at the consumer. Adapt the special-case hosts table and short-domain constant. Omit the Bitly/case-sensitive test hooks if you have no equivalent migrations/tests.

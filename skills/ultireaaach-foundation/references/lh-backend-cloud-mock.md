<!-- capsule-v2 -->
# Cloud-API mock for a vendored SPA — what does it take to bootstrap someone else's dashboard against a fake cloud backend?

**Source:** Ultireaaach `main@60bf4a3e478022df11ed2f04077d129f4f72cc60`; Codebase Memory `ultireaaach`. **Question:** the SPA hardcodes `https://dev.api.linkedhelper.com/v2/*`; which response contracts MUST the local mock honor so login, account creation, and list rendering work?

## Connected graph-selected seam
**Path/Symbol:** `packages/app/src/server.ts:fakeAccessToken` (68-81) + `handleLhBackend` (239-379).
**Signature:** `export function fakeAccessToken(): string`; `async function handleLhBackend(req, res, url)` mounted at `/lh-backend/*` (bridge rewrites the cloud origin there).
**Data Shape:** JWT payload fields jwt-decode actually reads: `exp` in MILLISECONDS, `userId`, `role`, `aclScopes`, `email`; signature ignored ("bW9jaw"). List endpoints render only from `{ data: [...], count }` envelopes; POST /linkedInAccounts must answer `{ id }` (dashboard does `Number(res.id)`).

### Decisive source
```ts
/** Build a fake-but-decodable JWT. jwt-decode only decodes the payload; the
 * dashboard requires payload.exp (ms), userId, role, aclScopes, email. */
export function fakeAccessToken(): string {
  const now = Date.now();
  const header = base64urlJson({ alg: "HS256", typ: "JWT" });
  const payload = base64urlJson({
    sub: "1", iat: Math.floor(now / 1000),
    exp: now + 6 * 60 * 60 * 1000,
    userId: 1, role: "owner", aclScopes: ["*"], email: "dev@local",
  });
  return header + "." + payload + ".bW9jaw";
}
// accounts persist next to the DB so restarts keep them:
const LI_STORE_FILE = process.env.ULTIREAAACH_LI_STORE ?? (process.env.ULTIREAAACH_DB ?? "./data/ultireaaach.db").replace(/\.db$/, "-") + "li-accounts.json";
```
**Flow:** authTokens -> mockAuthBody{accessToken,refreshToken,user} -> users/me + users/:id (workspace embeds) -> frontendSettings echo -> licenses/machines/simpleMachines fixtures -> linkedInAccounts CRUD against an in-memory array flushed to the JSON sidecar on every mutation (loadLiAccounts() runs at module load). Route tests are ordered EXACT-before-SUBSTRING: `users/\d+$` before frontendSettings, `workspaces/onboardings` before generic onboardings, plural machines before singular machine.
**Invariant:** envelope shapes are load-bearing — a flat array where the dashboard expects `{data,count}` renders an empty list ("logins isn't saving" bug class); exp must be ms not s or every retry re-logins.
**Probe:** `packages/app/test/li-proxy.test.ts` — "fakeAccessToken is a decodable JWT with a future exp"; "POST /lh-backend/v2/linkedInAccounts persists and GET returns the account" (round-trip through the real server).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ultireaaach", query: "fakeAccessToken", limit: 5 });
// observed: total 1 -> ultireaaach.packages.app.src.server.fakeAccessToken Function packages/app/src/server.ts 68-81
```

## Verdict
Adopt the contract-first mocking discipline: decode-path field list, envelope shapes, id-returning creates, sidecar persistence keyed off the DB path. Adapt endpoint vocabulary and fixture values to whichever SPA you host. Omit the LH license/machine fixtures outside LH-shaped dashboards.

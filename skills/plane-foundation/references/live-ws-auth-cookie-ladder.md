<!-- capsule-v2 -->
# WebSocket auth cookie/token ladder — how do you authenticate a browser WS connection when cookies may or may not ride the upgrade request?

**Source:** plane AGPL-3.0-only `preview@e056bbf9eb6b511cdc0a5823b1bd6922e561a485`; Codebase Memory `plane`. **Question:** Browser WebSocket clients cannot always send credential cookies on the upgrade (cross-site SDKs, native wrappers) — what fallback grammar authenticates the connection once and pins identity for its whole lifetime?

## Token-or-header credential ladder
**Path/Symbol:** `apps/live/src/lib/auth.ts:onAuthenticate` (:24–73) + `handleAuthentication` (:75–97); transport consumer `UserService.currentUser(cookie)` in `apps/live/src/services/user.service.ts` (:14–40); context type `HocusPocusServerContext`.
**Signature:** `onAuthenticate({ requestHeaders, requestParameters, context, token }): Promise<{ user: { id: string; name: string } }>`; `handleAuthentication({ cookie, userId }): Promise<{ user: { id, name } }>`.
**Data Shape:** `token` is the hocuspocus auth token: EITHER a JSON string `{ id: string; cookie: string }` (TUserDetails) OR anything non-JSON (parse failure tolerated). Query params carry routing context: `documentType`, `projectId`, `workspaceSlug`. Context fields fixed per connection: `cookie, documentType, projectId, userId, workspaceSlug`.

### Decisive source
```ts
try {
  const parsedToken = JSON.parse(token) as TUserDetails;
  userId = parsedToken.id; cookie = parsedToken.cookie;
} catch { logger.error("Token parsing failed, using request headers", appError); }
finally {
  if (!cookie) { cookie = requestHeaders.cookie?.toString(); }   // header fallback
}
if (!cookie || !userId) {
  throw new AppError("Credentials not provided", { code: "AUTH_MISSING_CREDENTIALS" });
}
context.cookie = cookie ?? requestParameters.get("cookie") ?? "";
// ... fill context.documentType/projectId/userId/workspaceSlug from query params ...
const user = await userService.currentUser(cookie);
if (user.id !== userId) { throw new AppError("Authentication unsuccessful: User ID mismatch"); }
```

**Flow:** try parsing the token as JSON carrying `{id, cookie}` (the frontend forwards the session cookie inside the token when the upgrade request can't carry it) → in `finally`, fall back to the raw `Cookie` request header if the token didn't provide one → hard-fail with typed `AUTH_MISSING_CREDENTIALS` if either piece is missing → stash credentials and routing params into the connection context → re-validate server-side: call the API's current-user endpoint WITH that cookie and reject with a mismatch error if the returned id differs from the claimed `userId` → return the display projection `{id, name}`. Any inner failure is rethrown as `"Authentication unsuccessful"` preserving the AppError code.
**Invariant:** The cookie is resolved exactly once at connect time and reused by every later service call for that socket (services read `context.cookie` via `getHeader()`), so mid-session auth revocation surfaces only as API failures, never as context mutation. Client-claimed identity is never trusted alone — the id must match what the backend says the cookie belongs to.
**Probe:** No dedicated upstream test. Deterministic pins: auth.ts contains `JSON.parse(token) as TUserDetails`, the `finally` header fallback, `code: "AUTH_MISSING_CREDENTIALS"`, and `user.id !== userId`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "plane", query: "onAuthenticate cookie token credentials websocket", limit: 5 });
```
Observed at pin: rank-2 = `onAuthenticate` (auth.ts :24–73); rank-1 is an unrelated decorator — scope citations by file path apps/live/src/lib/auth.ts.

## Verdict
Adopt the token-carried-cookie fallback grammar, parse-failure tolerance, typed missing-credential error, and claim-vs-cookie id cross-check; adapt where your session cookie lives and how the API validates it; omit Plane's query-param routing context shape if your host passes document scope differently. Coverage caveat: whole-file reads @ pin; no upstream tests exercise this ladder.

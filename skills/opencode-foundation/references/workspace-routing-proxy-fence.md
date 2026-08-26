<!-- capsule-v2 -->
# Workspace routing request plan — how does one server transparently serve many workspaces, including proxying to remote replicas with read-your-writes?

**Source:** opencode MIT `dev@03521003fafd`; Codebase Memory `opencode`. **Question:** How should a middleware decide per-request between local execution and remote proxying, resolve the target directory, and guarantee a proxied mutation is visible locally before its response returns?

## Tagged-enum plan + fence-blocking proxy
**Path/Symbol:** `packages/opencode/src/server/routes/instance/httpapi/middleware/workspace-routing.ts` (`RequestPlan` :31-42, `defaultDirectory` :86-88, `planRequest` :160-186, `proxyRemote` :113-146, `routeWorkspace` :188-210, `WorkspaceRoutingQueryFields` :22-27); context consumer at `middleware/instance-context.ts` (:23-35).
**Signature:** `workspaceRoutingLayer → WorkspaceRoutingMiddleware (provides WorkspaceRouteContext{directory, workspaceID?}, requires Session.Service)`; `proxyRemote(client, request, workspace, target, url) → Effect<HttpServerResponse>`.
**Data Shape:** `RequestPlan = InvalidWorkspace | MissingWorkspace{workspaceID} | Local{directory, workspaceID?} | Remote{request, workspace, target, url}`; `Target = {type:"local", directory} | {type:"remote", url, headers}`.

### Decisive source
```ts
// workspace-routing.ts:86-88 — directory resolution ladder:
return url.searchParams.get("directory") || request.headers["x-opencode-directory"] || process.cwd()
// :69-71 — session's stored workspace beats the query param:
return sessionWorkspaceID ?? (workspaceParam ? WorkspaceV2.ID.make(workspaceParam) : undefined)
// :121-127 — never proxy into a dead sync connection:
const syncing = yield* Workspace.Service.use((svc) => svc.isSyncing(workspace.id))
if (!syncing) return HttpServerResponse.text(`broken sync connection for workspace: ${workspace.id}`, { status: 503 })
// :132-143 — READ-YOUR-WRITES: hold the response until the local replica catches up:
const sync = Fence.parse(new Headers(response.headers))
if (sync) yield* Fence.wait(workspace.id, sync, ...)
```

**Flow:** middleware reads session (via `getWorkspaceRouteSessionID`, tolerating NotFound/defects as undefined) ⇒ picks workspaceID (session > `?workspace=`, strict ID-schema validation ONLY on `/api/*`; invalid → 400 InvalidRequestError) ⇒ resolves workspace from control plane; unknown id without env-workspace override → 500 "Workspace not found" ⇒ if resolved and route is not control-plane (`isLocalWorkspaceRoute` or `/console` prefix stays local): local targets swap the route directory; remote targets proxy. Proxy contract: append original path to base URL, preserve other query params, DROP `workspace`, strip hop-by-hop `x-opencode-*` headers, inject adapter auth headers, upgrade websocket upgrades transparently, then block on the fence header before returning.
**Invariant:** The middleware cannot declare query params in effect-smol, so `directory`/`workspace` fields MUST be spread into every routed endpoint's query schema or HttpApi 400-rejects requests that carry them (documented inline :17-21). Control-plane routes always execute locally even with a workspace selected. `decode()` of the directory is try/catch-tolerant.
**Probe:** `packages/opencode/test/server/httpapi-workspace-routing.test.ts` — ":261 proxies remote HTTP" pins path-append/query-preserve/workspace-strip/header-strip/target-auth-inject; ":330 waits for sync fence headers"; ":392 503 broken sync"; ":412 WS echo through proxy"; ":445 missing workspace 500"; ":505 directory query/header fallback"; source pin:
```bash
grep -n 'middleware-declared query schemas' packages/opencode/src/server/routes/instance/httpapi/middleware/workspace-routing.ts
```
expect 1 hit at :21.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "workspace routing middleware proxy remote target RequestPlan defaultDirectory", limit: 8 });
```

## Verdict
Adopt the tagged request-plan shape, the three-step directory ladder, session-precedence for workspace selection, strict-param validation only on v2 paths, and fence-blocked proxying; adapt the adapter/target model and header conventions; omit opencode's specific control-plane route list.

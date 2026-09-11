<!-- capsule-v2 -->
# Identity provider SPI + auth gate — how does a single-authority daemon gain pluggable multi-user authentication without touching every route?

**Source:** localterm MIT `fix/pi-extension-native-import@f26c5853`; Codebase Memory `localterm`. **Question:** How do you bolt header-proxy / passkey / OIDC login onto an existing no-auth daemon so route handlers never change and the legacy behavior is byte-identical when no provider is configured?

## One SPI, one gate, one owner partition
**Path/Symbol:** `packages/server/src/identity/types.ts:IdentityProvider` (:24–37), `resolve.ts:createIdentityResolver` (:33–36) + `createAuthGateMiddleware` (:51–73) + `toSessionOwner` (:38–39), `factory.ts:createIdentityProvider` (:11–23); wiring `packages/server/src/index.ts:2399–2447`.
**Signature:** `identify(context: Context, sourceIp: string | null): Identity | null`; optional `routes?: () => Hono` (the provider closes over its own stores/secret/origin).
**Data Shape:** `Identity { user, displayName? }`; `SessionOwner = string | null` (null = operator/legacy tier); deps injected as `{ secret, getOrigin, stateDirectory }`; config is a zod discriminated union on `provider` (`schemas.ts:1744`, strict — extra keys rejected).

### Decisive source
```ts
async (context, next) => {
    if (!provider?.denyUnauthenticated) return await next();
    const requestPath = context.req.path;
    const isProtected =
      (requestPath === "/ws" || requestPath.startsWith("/api/")) && requestPath !== "/api/health";
    if (!isProtected) return await next();
    const authorization = context.req.header("authorization");
    if (
      provider.operatorToken &&
      authorization &&
      timingSafeEqualString(authorization, `Bearer ${provider.operatorToken}`)
    ) {
      return await next();
    }
    const identity = resolveIdentity(context, getRequestSourceIp(context));
    if (!identity) return context.json({ error: "unauthorized" }, HTTP_STATUS_UNAUTHORIZED);
    await next();
  };
```

**Flow:** config → exhaustive factory switch → provider instance; daemon mounts `app.use("*", createAuthGateMiddleware(provider, resolveIdentity))` then `app.route("/auth", provider.routes())`. HTTP routes resolve identity via conninfo; the WS upgrade instead passes the RAW socket remoteAddress into `resolveIdentity` (`index.ts:3150–3155`) because it is more authoritative at upgrade time. The resolved identity becomes the SessionOwner partition key: SessionManager scopes list/attach/kill by owner; cross-tenant attach returns null (caller spawns fresh), operator tier (null owner) sees all; with NO provider every request resolves null — pre-identity behavior preserved exactly.
**Invariant:** "Silence means admin" is scoped per provider kind: only a provider that sets `denyUnauthenticated: false` may map a no-identity request to the operator tier (header mode — network position vouches); self-authored modes must reject at the door because nothing external vouches for silence. The operator bearer token exists precisely because a CLI cannot run a WebAuthn/OIDC ceremony, and is compared timing-safe BEFORE identity resolution. `/api/health` stays exempt so readiness needs no session.
**Probe:** `packages/server/tests/passkey.test.ts` createAuthGateMiddleware describe — unauthenticated /api → 401 :170–178, valid cookie admits :180–199, bearer ladder (none→401, wrong→401, valid→200) :201–222, /api/health + static exempt :224–233, header mode not gated :235–242; `packages/server/tests/identity.test.ts` owner-partition suite :116–152 (list/attach/kill scoped; null sees all). Executed this pass: all four identity suites 42/42 green.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "localterm", name_pattern: "IdentityProvider|IdentityResolver|createAuthGateMiddleware|toSessionOwner", limit: 12 });
```
Executed live: factory :11–23, gate :52–73, resolver :33–36, SPI interface types.ts :24–37 all rank with exact lines; `trace_path(toSessionOwner, inbound)` shows consumers {buildApiRoutes, createServer, onOpen, ownerFor, sessions}.

## Verdict
Adopt the shape: provider interface + denyUnauthenticated flag + optional routes() + one global gate middleware + owner partition key; adapt protected-path prefixes, health exemptions, and the CLI escape hatch to your host; omit OIDC/passkey specifics until needed (they slot in behind the same SPI). Traps: gating static/login surfaces locks you out of the login page itself; resolving WS identity from proxy-derived conninfo instead of the raw socket lets upgrade-time spoofing win.

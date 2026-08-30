<!-- capsule-v2 -->
# Role-impersonation client plane — how does the client produce the impersonation wrapper and JWT that the SQL guard ladder's line-rewind consumes?

**Source:** Supabase Apache-2.0 `master@a18253f7c7d3a967bf91599c9dcf8ae704b7d686`; Codebase Memory `supabase`. **Question:** Where do the `isRoleImpersonationEnabled` flag and the wrapped SQL that pass-1's execute-sql guard ladder rewinds actually come from, and how do async claim resolutions stay correct across stale tabs and expiring tokens?

## Wrapper + JWT minting (`lib/role-impersonation.ts`)
**Path/Symbol:** `apps/studio/lib/role-impersonation.ts` : `wrapWithRoleImpersonation` (:152-164), `getExp1HourFromNow` (:96-98), `getPostgrestClaims` (:100-141), `encodeBase64Url` (:170-177), `genKey` (:179-187), `createToken` (:189-206), `getRoleImpersonationJWT` (:208-219).
**Signature:** `wrapWithRoleImpersonation(sql: SafeSqlFragment, state?: { role?: ImpersonationRole; claims?: PostgrestClaims }): SafeSqlFragment`; `getRoleImpersonationJWT(projectRef: string, jwtSecret: string, role: PostgrestImpersonationRole): Promise<string>`.
**Data Shape:** identity path — `role === undefined` returns the input SQL unchanged (no wrapper, no sentinel row). Wrapped path — claims are spread-copied with `exp` re-stamped to now+1h (`unexpiredClaims`) before delegating to pg-meta's `getImpersonationSQL({role, unexpiredClaims, sql})`, which prepends the pinned 11-line preamble (pass-1 contract). Three claim shapes: native authenticated (aud `'authenticated'`, iss `https://{ref}.supabase.co/auth/v1`, fresh `session_id` uuidv4, sub = user.id), external authenticated (sub + `additionalClaims` SPREAD onto the claim object), anon/service_role (minimal `{iss:'supabase', ref, role, iat, exp}`). The JWT is minted entirely in-browser: HS256 via `window.crypto.subtle` (raw HMAC-SHA-256 importKey → sign) and base64url via `btoa` + `+→- /→_ strip trailing =`.

### Decisive source
```ts
export function wrapWithRoleImpersonation(
  sql: SafeSqlFragment,
  state?: RoleImpersonationState
): SafeSqlFragment {
  const { role, claims } = state ?? { role: undefined, claims: undefined }

  if (role === undefined) return sql

  const unexpiredClaims =
    claims !== undefined ? { ...claims, exp: getExp1HourFromNow() } : undefined
  const impersonationSql = getImpersonationSQL({ role: role, unexpiredClaims, sql })
  return impersonationSql
}
```

**Flow:** user picks a role → `setRole` resolves claims (possibly via an RPC hook) → every subsequent SQL run calls `wrapWithRoleImpersonation`, which re-stamps `exp` at wrap time so a once-resolved claim set never expires mid-session → pg-meta builds the 11-line preamble → execute-sql's LINE-rewind (pass-1) undoes exactly that height. Self-hosted projects additionally let the studio mint a valid PostgREST JWT client-side from the project's own secret.
**Invariant:** the wrapper height stays pinned to `ROLE_IMPERSONATION_SQL_LINE_COUNT` (11) — any change to `getImpersonationSQL`'s preamble must move the rewind constant or error line numbers drift. Claims are re-stamped at WRAP time, never trusted to have been fresh at resolution time.
**Probe:** `apps/studio/lib/role-impersonation.test.ts` (pure vitest, read whole; unexecutable in-lane — standing block) pins: identity path returns the same SQL when role is undefined; anon/native/external wraps contain `set_config('role', …)`, `request.jwt.claims`, `ROLE_IMPERSONATION_NO_RESULTS`, and the original SQL; custom roles emit `set local role '<name>'`.

## Claim-resolution state plane (`state/role-impersonation-state.tsx`)
**Path/Symbol:** `apps/studio/state/role-impersonation-state.tsx` : `useCustomizeAccessToken` (:32-51), `resolveRoleClaims` (:56-73), `createRoleImpersonationState` (:75-103), `useLocalRoleImpersonationState` (:146-174), `useControlledRoleImpersonationState` (:183-254, guards at :201 and :235).
**Signature:** `resolveRoleClaims(projectRef, role, customAccessTokenHookDetails?, customizeAccessToken): Promise<PostgrestClaims | undefined>`; controller shape `{ role, claims, setRole }`.
**Data Shape:** three scopes share ONE resolver: project-wide valtio context, per-instance local state (notebook cells), and externally-controlled state (role persisted per query tab). The customize-access-token hook is invoked THROUGH executeSql itself: `safeSql\`select ${ident(schema)}.${ident(functionName)}(${literal(JSON.stringify(event))}::jsonb) as event;\`` with event `{user_id: claims.sub, claims, authentication_method:'password'}`; its output is arbitrary user-defined Postgres and is trusted wholesale (in-source comment). Custom roles resolve to `undefined` claims.

### Decisive source
```ts
// Guards against re-resolving claims for a role change that `setRole` below just resolved
// itself — without it, every selection would re-run the (possibly RPC-backed) resolution
// twice: once eagerly in `setRole`, once again here once `role` updates on the next render.
const skipNextResolveRef = useRef(false)
// ...
// Captured before the await: if the controlling tab changes while this resolution is
// in flight, `onRoleChangeAtCallTime` will point at a different tab's callback by the
// time we get here. Comparing against the captured reference lets us detect that and
// discard the result instead of writing this role/claims into the wrong tab.
const onRoleChangeAtCallTime = onRoleChangeRef.current
const nextClaims = await resolveRoleClaims(...)
if (onRoleChangeRef.current !== onRoleChangeAtCallTime) return
skipNextResolveRef.current = true
```

**Flow:** setRole resolves claims eagerly AND updates the controlled role → the effect watching the role skips exactly one re-resolution (`skipNextResolveRef`) → if the controlling tab changed during the await, the stale result is discarded before any write. Claims are always local/derived (time-bound tokens) even when the role is persisted.
**Invariant:** an eager-resolve + watch pattern needs BOTH guards: skip-next prevents double RPC resolution; capture-before-await prevents cross-tab stale writes. Drop either and you get duplicate hook calls or role/claims written into the wrong tab.
**Probe:** no dedicated upstream test for the state file (the lib test covers the pure half); behavior confirmed by direct read of both guard sites and their in-source rationale comments.

## Get live surrounding code
**Retrieve:** Codebase Memory MCP was NOT connected in this session; per AGENTS.md fallback this seam was confirmed by direct whole-file reads of both files plus the direct test at the pin. Revalidate with:
```ts
await mcp.codebase_memory.search_graph({ project: "supabase", query: "wrapWithRoleImpersonation getRoleImpersonationJWT resolveRoleClaims useControlledRoleImpersonationState", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-piece producer contract: identity-path wrapper (undefined role ⇒ untouched SQL), wrap-time exp re-stamping, and the two async-hygiene guards (skip-next-resolve, capture-before-await stale-write discard) — all port verbatim to any dashboard running SQL under selectable roles. Adapt the in-browser HS256 minting to your host's secret policy (omit it where secrets never reach the browser; keep the claims shapes). Omit Supabase-specific issuer URLs and the customize-access-token RPC unless your platform has an equivalent user-defined hook. Caveat: state-plane guards verified by direct read only — no dedicated upstream test exists for them.

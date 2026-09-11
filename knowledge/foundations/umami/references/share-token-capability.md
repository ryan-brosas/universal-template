<!-- capsule-v2 -->
# Share-token capability model — how do you grant scoped, type-tagged read access to analytics without accounts?

**Source:** umami v3.3.1 / MIT @ master`ca661c70`; Codebase Memory `ext-umami`. **Question:** How are share links minted, bound to entity scope (incl. board membership), and enforced on every API call?

## share-token-capability
**Path/Symbol:** mint `src/app/api/share/[slug]/route.ts:GET :166-215`; enforce `src/lib/auth.ts:parseShareToken :104-120` + `src/permissions/website.ts:canViewWebsite :7-40`.
**Signature:** `createToken({...data, type: SHARE_TOKEN_TYPE}, secret())` — UNSIGNED-ENCRYPTED? No: plain JWT (createToken), verified by parseToken; accepted only when `token.type === SHARE_TOKEN_TYPE`.
**Data Shape:** token carries websiteId/pixelId/linkId OR board websiteIds/pixelIds/linkIds arrays; requests must ALSO carry the share context header.

### Decisive source
```ts
// auth.ts — type gate blocks cross-token replay:
// "This prevents other tokens signed with the same secret (e.g. the cache token from
//  /api/send) from being replayed as share tokens to gain analytics access."
if (token?.type !== SHARE_TOKEN_TYPE) return null;
// context gate: a stolen header-only token outside the share app is useless
const shareContext = request.headers.get(SHARE_CONTEXT_HEADER);
if (!shareContext) return null;
```

**Flow:** public slug → resolve share row → for BOARDS, every member entity id is re-checked through canView* filters at MINT time (revoked members silently drop out) → embed ids + white-label into token → client calls APIs with share token; permission layer treats `shareToken.websiteId === id` as view grant.
**Invariant:** share grants are VIEW-only by construction (they never reach canUpdate/canDelete paths). Board shares snapshot authorization AT RESOLUTION TIME — later permission changes require re-resolving the slug, not just re-presenting an old token.
**Probe:** structural pins: `grep -n "SHARE_TOKEN_TYPE" src/lib/auth.ts | head -2` → :108 region; `grep -c "filterBoardEntityIdsForShare" src/app/api/share/\[slug\]/route.ts` → ≥2 lines.
**Probe:** `grep -n "SHARE_CONTEXT_HEADER" src/lib/auth.ts` → :9,:66.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "ext-umami", query: "parseShareToken SHARE_TOKEN_TYPE getShareByCode", limit: 10 });
```
**(Retrieve:)**

## Verdict
Adopt type-tagged capability tokens + mint-time scope expansion for public sharing; adapt to signed-encrypted tokens if confidentiality matters; keep the context-header binding for embed surfaces.

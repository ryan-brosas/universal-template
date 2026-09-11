<!-- capsule-v2 -->
# MCP App permission intersection — how do server-requested iframe capabilities get granted?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f...`; Codebase Memory `ai`. **Question:** How do the server's requested `permissions` and the host's `allowedPermissions` combine into an iframe `allow` attribute?

## Set-intersection deny-by-default permissions
**Path/Symbol:** `packages/react/src/mcp-apps/sandbox.ts` — `getMCPAppAllowAttribute` (:129–142), `MCP_APP_PERMISSION_FEATURES` map (:106–111), `MCPAppPermission` union (:100–104); consumed at `packages/react/src/mcp-apps/app-frame.tsx:72–75`.
**Signature:** `getMCPAppAllowAttribute(permissions?: Record<string,unknown>, allowedPermissions?: MCPAppPermission[]): string | undefined`.
**Data Shape:** features: `camera`, `microphone`, `geolocation`, `clipboardWrite→clipboard-write`; result joined with `'; '` (Permissions-Policy syntax) or undefined when empty.

### Decisive source
```ts
if (permissions == null || allowedPermissions == null) return undefined;
const allow = allowedPermissions
  .filter(permission => Boolean(permissions[permission]))   // BOTH sides required
  .map(permission => MCP_APP_PERMISSION_FEATURES[permission]);
return allow.length > 0 ? allow.join('; ') : undefined;
```

**Flow:** MCP App resource `_meta.ui.permissions` = what the SERVER wants → host config `sandbox.allowedPermissions` = what the HOST tolerates → attribute lists only the INTERSECTION → `<iframe allow={resourceAllow} sandbox={outerSandbox ?? 'allow-scripts allow-same-origin allow-forms'}>`. The in-source comment states why hierarchy matters: Permissions Policy is hierarchical, so the OUTER frame must delegate a feature for the sandbox proxy to re-delegate to the inner app frame.
**Invariant:** Deny-by-default on BOTH axes: omitting the host allowlist grants nothing (even if the server begs), and omitting server permissions means nothing is requested. A porter who defaults missing sides to "grant" turns any malicious server metadata into camera/mic access. Defaults: outer `'allow-scripts allow-same-origin allow-forms'` (:49–50) vs inner `'allow-scripts allow-forms'` (:55) — the inner frame deliberately lacks same-origin.
**Probe:** deterministic: `grep -n clipboard-write packages/react/src/mcp-apps/sandbox.ts` → `110:`; `grep -n "allowedPermissions == null" packages/react/src/mcp-apps/sandbox.ts` → `133:`; `grep -n hierarchical packages/react/src/mcp-apps/app-frame.tsx` → `184:`. Direct tests: `sandbox.test.ts:106` denies without allowlist, `:117` intersection-only grant, `:126` clipboardWrite mapping; `app-frame.test.tsx:66/:75/:83` DOM-level delegation.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "getMCPAppAllowAttribute permissions", limit: 10, fields: ["signature","name","file"] });
// verified live @9d9a73f: rank#1 sandbox.getMCPAppAllowAttribute :129-142
```

## Verdict
Adopt the two-sided intersection and the feature-name mapping; adapt the permission vocabulary to your platform's policy features; omit nothing — one-sided granting is the security hole.

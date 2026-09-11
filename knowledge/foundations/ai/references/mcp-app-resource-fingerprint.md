<!-- capsule-v2 -->
# MCP App resource fingerprint — how do you detect a changed app resource without a shared hash utility?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f...`; Codebase Memory `ai`. **Question:** How is a `ui://` app resource content-fingerprinted for drift detection, and why does the code duplicate canonicalJSON?

## Canonical-JSON SHA-256 drift detector
**Path/Symbol:** `packages/mcp/src/tool/mcp-app-fingerprint.ts` — `fingerprintMCPAppResource` (:45–59), `canonicalJSON` (:16–28), `toBase64url` (:30–35), `detectMCPAppResourceDrift` (:65–70); twin implementation `packages/ai/src/util/canonical-hash.ts:hashCanonical`.
**Signature:** `fingerprintMCPAppResource(resource: MCPAppResource): Promise<string>`; `detectMCPAppResourceDrift(current: string, baseline: string): boolean`.
**Data Shape:** hashed payload = `canonicalJSON({html, csp: meta?.csp ?? null, permissions: meta?.permissions ?? null})`; output base64url (unpadded) SHA-256.

### Decisive source
```ts
// canonicalJSON/toBase64url/the digest below mirror
// packages/ai/src/util/canonical-hash.ts, which `@ai-sdk/mcp` can't import
// (wrong dependency direction, not exported). Keep them identical; if a third
// consumer appears, hoist into @ai-sdk/provider-utils instead.
const digest = await crypto.subtle.digest('SHA-256',
  encoder.encode(canonicalJSON({
    html: resource.html,
    csp: resource.meta?.csp ?? null,
    permissions: resource.meta?.permissions ?? null,
  })));
return toBase64url(new Uint8Array(digest));
```

**Flow:** capture baseline fingerprint on first load → later reads re-fingerprint → strict string inequality ⇒ drift. Key-sorting inside `canonicalJSON` makes the digest independent of key insertion order (test pins that `{a,b}` vs `{b,a}` CSP/permission objects hash equal). Absent metadata hashes as literal `null`, so adding/removing a whole csp or permissions block CHANGES the digest — only key order and formatting don't.
**Invariant:** The duplication is deliberate dependency-direction hygiene, not an oversight: leaf packages must not import upward into `@ai-sdk/ai`. A porter who "fixes" the duplication by importing across packages couples the MCP client to the full SDK. Drift detection compares DIGESTS ONLY — baseline storage stays the host's concern (mirrors `fingerprintTools` in `tool-fingerprinting.md`).
**Probe:** deterministic: `grep -n "wrong dependency direction" packages/mcp/src/tool/mcp-app-fingerprint.ts` → `8:`; `grep -n "permissions: resource.meta?.permissions ?? null" packages/mcp/src/tool/mcp-app-fingerprint.ts` → `54:`. Direct tests: `mcp-app-fingerprint.test.ts:22` stable digest, `:28` key-order invariance, `:48` mutation sensitivity.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "fingerprintMCPAppResource canonicalJSON", limit: 10, fields: ["signature","name","file"] });
// verified live @9d9a73f: rank#1 mcp-app-fingerprint.fingerprintMCPAppResource :45-59
```

## Verdict
Adopt the field selection (html + csp + permissions with null-presence semantics) and canonical serialization; adapt storage/rotation of baselines to your host; when porting BOTH sides, keep them byte-identical or extract to the shared utils layer exactly as the in-source comment prescribes.

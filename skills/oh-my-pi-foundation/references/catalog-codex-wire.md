<!-- capsule-v2 -->
# Codex JWT claims — how do you extract account id and data residency from a ChatGPT OAuth token?

**Source:** Oh My Pi MIT `main@96f428097`; Codebase Memory `oh-my-pi`. **Question:** Which request headers does the ChatGPT-backend Codex wire need, and what comes from the token itself?

## Header vocabulary + fail-soft JWT claim readers + no-clobber residency application
**Path/Symbol:** `packages/catalog/src/wire/codex.ts:OPENAI_HEADERS` (:12), `JWT_CLAIM_PATH` (:48), `getCodexAccountId` (:54), `getCodexResidency` (:80), `applyCodexResidencyHeader` (:104).
**Signature:** `getCodexAccountId(accessToken): string | undefined`; `getCodexResidency(accessToken): string | undefined`; `applyCodexResidencyHeader(headers: Headers | Record<string,string>, accessToken): void`.
**Data Shape:** claim key is the literal URL `"https://api.openai.com/auth"`; residency prefers `chatgpt_data_residency`, falls back to `chatgpt_compute_residency`.

### Decisive source
```ts
// Enterprise ChatGPT workspaces pinned to a region reject Codex requests
// whose egress doesn't match — HTTP 401 "Workspace is not authorized in this
// region." — unless the client DECLARES the residency itself. The token
// already carries it, so no configuration is needed.
for (const claim of [auth?.chatgpt_data_residency, auth?.chatgpt_compute_residency]) {
  if (typeof claim !== "string") continue;
  const residency = claim.trim();
  if (residency.length > 0) return residency;
}

// Adds residency WITHOUT replacing a caller-supplied value (both Headers and
// plain-record shapes, case-insensitive check on records).
if (headers instanceof Headers) { if (headers.has(headerName)) return; /* … */ }
```

**Flow:** split token on `.` → require exactly 3 parts → base64-decode payload → read namespaced auth claim → return undefined on ANY malformed input (non-JWT tokens from Codex-compatible proxies are common) → residency header applied per-request only when absent.
**Invariant:** (1) every reader returns undefined instead of throwing — an unparseable token must not break request assembly; (2) blank/non-string claims are skipped, never sent as empty header values; (3) caller-set headers always win over token-derived ones; (4) the pinned client version (`CODEX_CLIENT_VERSION`) tracks the upstream codex package because the backend gates on it.
**Probe:** direct `packages/catalog/test/codex-wire.test.ts:16–60` (residency preference ladder, blank-claim skip, opaque non-JWT keys, no-clobber semantics).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "getCodexResidency getCodexAccountId OPENAI_HEADERS codex jwt", limit: 10, fields: ["signature", "file"] });
```

## Verdict
Adopt the fail-soft claim extraction and token-derived residency declaration; adapt header names as the upstream client evolves; omit attestation/residency if you use plain API keys. Coverage caveat: none.

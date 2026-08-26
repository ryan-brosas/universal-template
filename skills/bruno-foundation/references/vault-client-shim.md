<!-- capsule-v2 -->
# Vault client shim — node-vault-compatible HTTP client with health-endpoint status amnesty

**Source:** bruno MIT `main@675965612ff11b23bc9b6c9541110a287bcb2967`; Codebase Memory `ext-bruno`. **Question:** How do you replace a heavy SDK (node-vault) with a minimal axios client that stays drop-in compatible — including its error shapes and its weird health-check semantics?

## Connected graph-selected seam
**Path/Symbol:** `packages/bruno-requests/src/utils/node-vault.ts:handleVaultResponse` (:109-131), `VaultError` (:48-70), `createVaultClient` (:148-326).
**Signature:** `createVaultClient(config?: VaultConfig) → VaultClient` with `{read(path), write(path,data), approleLogin(args), tokenLookupSelf(), tokenRenewSelf({increment})}`.
**Data Shape:** mutable client props (`endpoint`, `token`, `namespace`, `apiVersion`) read per-request; headers `X-Vault-Token`, `X-Vault-Namespace`; axios `validateStatus: () => true` so ALL statuses flow through the local classifier.

### Decisive source
```ts
function handleVaultResponse(statusCode: number, body: any, path: string): any {
  if (statusCode === 200 || statusCode === 204) return body;
  // Health endpoint special handling (matches node-vault behavior)
  if (path.match(/sys\/health/) !== null) return body;
  let message = body?.errors?.length > 0 ? body.errors[0] : `Status ${statusCode}`;
  throw new VaultError(message, { statusCode, body });
}
```

**Flow:** merge config-level + per-call requestOptions → build `${endpoint/(apiVersion)}${path}` (trailing-slash normalized) → JSON content-type + token/namespace headers → send with `proxy:false`, never throw on status → classify: 200/204 pass; any `/sys/health/` path passes REGARDLESS of status (health checks return 429/472/501/503 by design to encode seal state — matching node-vault's amnesty is what makes this drop-in); everything else throws `VaultError` carrying BOTH `response.statusCode` and aliased `response.status` plus raw body.
**Invariant:** strictSSL=false ⇒ agent with rejectUnauthorized:false; ca ⇒ bespoke agent; agent only created when needed. Error compatibility is dual-field (`statusCode` for node-vault callers, `status` for axios-style handlers) — dropping either alias breaks one consumer class silently.
**Probe:** `packages/bruno-requests/src/utils/node-vault.spec.ts` :696-716 — 'should not throw error for sys/health even with non-200 status' pins the amnesty clause.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-bruno", query: "handleVaultResponse VaultError createVaultClient", limit: 5 });
```

## Verdict
Adopt validateStatus-true + local classification, health-path amnesty, dual-shaped errors, lazy TLS agents. Adapt method surface to your secret backend; omit AppRole specifics if unused. Coverage caveat: none — clean coverage at pin.

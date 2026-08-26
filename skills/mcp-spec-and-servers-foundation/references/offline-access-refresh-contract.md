<!-- capsule-v2 -->
# Offline-Access Refresh Contract — who may request `offline_access`, who must never advertise it, and what guarantees nothing?

**Source:** modelcontextprotocol/specification MIT `main@57ac4a2e`; Codebase Memory `modelcontextprotocol`. **Question:** How do MCP clients, resource servers, and authorization servers each handle refresh-token acquisition via the OIDC `offline_access` scope without breaking the OAuth 2.1 role model?

## Tri-party contract (SEP-2207, Final → GA normative)
**Path/Symbol:** `docs/seps/2207-oidc-refresh-token-guidance.mdx` (whole; client requirements :87–103; RS requirements :105–113; rationale :115–146; security :175–198) × GA absorption `docs/specification/2026-07-28/basic/authorization/index.mdx` :299–313 (Refresh Tokens).
**Signature:** scope assembly: `scopes = rs_scopes ∪ (offline_access if 'offline_access' ∈ AS_metadata.scopes_supported and client_wants_refresh else {})`.
**Data Shape:** three roles with asymmetric duties:
1. **Client (wants refresh):** MUST keep refresh tokens confidential in transit + storage (OAuth 2.1 §4.3); SHOULD include `refresh_token` in its `grant_types` client metadata (advertise capability); MAY add `offline_access` to the scope of authorization AND token requests — but ONLY when the AS metadata lists it in `scopes_supported`; MUST NOT assume advertising/requesting guarantees issuance ("the Authorization Server retains discretion based on its policies").
2. **MCP server (Protected Resource):** SHOULD NOT include `offline_access` in the `WWW-Authenticate` challenge `scope`, SHOULD NOT list it in Protected Resource Metadata `scopes_supported` — "as refresh tokens are not a resource requirement".
3. **Authorization server:** decides issuance from client capability (registered grant types) + policy; MAY apply risk-based extra checks because `grant_types` is self-reported (domain allowlists, reputation, verification) rather than trusting metadata alone.

### Decisive source
```md
# index.mdx :304–313 (GA Refresh Tokens section)
MCP Clients that desire refresh tokens:
- MUST keep refresh tokens confidential ...
- SHOULD include `refresh_token` in their `grant_types`
- MAY add `offline_access` to the scope parameter of the
  authorization and token requests WHEN the Authorization
  Server metadata contains it in `scopes_supported`
- MUST NOT assume refresh tokens will be issued; the AS retains discretion
MCP Servers (Protected Resources) SHOULD NOT include
`offline_access` in WWW-Authenticate scope or Protected
Resource Metadata scopes_supported, as refresh tokens are
not a resource requirement.
```

**Flow:** client reads AS metadata → sees `offline_access` ∈ `scopes_supported` → adds it to the resource's scopes for both the authorization request and the token exchange → AS issues (or withholds) a refresh token per its own policy → on later insufficient-scope challenges the client re-authorizes with the UNION of prior scopes + challenge scopes (step-up flow), re-requesting `offline_access` alongside so the refresh capability survives re-consent.
**Invariant:** `offline_access` is a CLIENT↔AS desire signal, never a RESOURCE requirement — the semantic error a porter commits is copying it into `WWW-Authenticate`/PRM `scopes_supported`, which claims the resource *requires* long-lived tokens. The dual gate (AS advertises it in `scopes_supported` AND client wants persistence) exists because some ASes issue refresh tokens ONLY on explicit request; clients that never ask get session-length access only and users see frequent re-auth prompts (the interoperability gap this SEP closes). For public clients, ASes MUST rotate refresh tokens (OAuth 2.1 §4.3.1, per security-considerations :34).
**Probe:** no runtime tests in the spec repo. Deterministic anchors: GA absorption verbatim at `authorization/index.mdx` :299–313; SEP Final status; SDK reference implementations promised in TS/Python SDKs (:200–208). Coverage caveat recorded honestly.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "modelcontextprotocol", name_pattern: "refresh-tokens|offline.access", limit: 10 });
```

## Verdict
Adopt the dual-gate client rule (want refresh ⇒ declare `refresh_token` grant + add `offline_access` only when AS-advertised, expect no guarantee), the RS prohibition on ever advertising `offline_access`, and the risk-based AS posture over self-reported metadata; adapt your secure storage and rotation handling to host platform; omit per-resource refresh semantics entirely — and remember step-up re-auth must carry previously-granted scopes (including `offline_access`) forward or users lose their sessions on every scope upgrade.

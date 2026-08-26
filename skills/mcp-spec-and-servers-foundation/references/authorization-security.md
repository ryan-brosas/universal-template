<!-- capsule-v2 -->
# Authorization Security — which OAuth 2.1 security requirements MUST an MCP client and server enforce, and why?

**Source:** modelcontextprotocol/specification MIT `main@4df2d6b`; Codebase Memory `modelcontextprotocol`. **Question:** What are the non-negotiable security gates (PKCE, `iss` validation, audience binding, no token passthrough) that a secure MCP auth implementation must enforce?

## The security gates
**Path/Symbol:** `docs/specification/draft/basic/authorization/security-considerations.mdx` (whole; token audience :14–23; token theft :25–34; communication :36–43; auth code protection :45–61; mix-up :63–65; open redirection :67–80; CIMD security :82–105; confused deputy :107–114; token privilege restriction :116–131).

### Decisive source
```md
# security-considerations.mdx:50-61 (PKCE is mandatory)
MCP clients MUST implement PKCE (OAuth 2.1 §7.5.2) and MUST verify PKCE
support before proceeding. MUST use the S256 code challenge method when
technically capable. Since OAuth 2.1/PKCE define no discovery mechanism:
- OAuth 2.0 AS Metadata: if `code_challenge_methods_supported` is absent,
  the AS does not support PKCE and clients MUST refuse to proceed.
- OIDC Discovery: MUST verify `code_challenge_methods_supported` presence;
  if absent, clients MUST refuse to proceed.
```

**Token audience binding & validation:** clients MUST include the `resource` parameter (RFC8707) in auth + token requests; servers MUST validate tokens were issued specifically for them. Token passthrough is explicitly forbidden (see Security Best Practices).

**Token theft:** clients/servers MUST implement secure token storage (OAuth 2.1 §7.1). ASes SHOULD issue short-lived access tokens; for public clients ASes MUST rotate refresh tokens (OAuth 2.1 §4.3.1).

**Communication security:** all AS endpoints MUST be HTTPS; all redirect URIs MUST be `localhost` or HTTPS.

**Authorization code protection:** PKCE mandatory (S256 when capable); verify PKCE support via AS metadata before proceeding (see decisive source). ASes providing OIDC Discovery MUST include `code_challenge_methods_supported` in metadata.

**Mix-up attacks:** an attacker controlling one AS may try to get the client to send it a code/token issued by a different honest AS. Mitigation is the `iss` authorization-response validation (see `authorization-overview`): record the expected issuer from validated metadata, compare the `iss` in the response (simple string comparison per RFC3986 §6.2.1), reject on mismatch, and apply the metadata-keyed table (if `authorization_response_iss_parameter_supported:true` and `iss` absent → reject; if false/absent and `iss` absent → proceed).

**Open redirection:** clients MUST have redirect URIs registered with the AS; ASes MUST validate exact redirect URIs against pre-registered values; clients SHOULD use + verify `state` params and discard mismatches; ASes MUST take precautions against redirecting to untrusted URIs.

**CIMD security:** ASes fetching metadata docs SHOULD consider SSRF risks; CIMD can't prevent `localhost` URL impersonation by itself (ASes SHOULD warn on localhost-only redirect URIs, MAY require attestation, MUST display the redirect URI hostname); ASes MAY implement domain-based trust policies.

**Confused deputy:** MCP proxy servers using static client IDs MUST obtain user consent for each dynamically-registered client before forwarding to third-party ASes.

**Access token privilege restriction:** servers MUST validate tokens before processing (OAuth 2.1 §5.2), MUST only accept tokens intended for themselves (audience claim / intended-recipient check), MUST reject tokens not bound to them, and MUST NOT pass through a client's token to upstream APIs (upstream uses a separate token from the upstream AS).

**Invariant:** every gate is a hard MUST — PKCE-verified-before-proceed, `iss`-validated responses, audience-bound tokens, HTTPS-only endpoints, no token passthrough. A porter who skips PKCE verification, who doesn't validate `iss`, who accepts tokens for other resources, or who forwards a client token upstream violates the security model.

**Probe:** no runtime tests in the spec repo; prose-normative with OAuth 2.1 / RFC9207 / RFC8707 anchors. Coverage caveat recorded honestly.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "modelcontextprotocol", name_pattern: "Audience|Passthrough|Refresh-Tokens", limit: 10 });
```

## Verdict
Adopt the mandatory security gates — PKCE (S256, verified via metadata before proceeding), `iss` authorization-response validation, audience-bound tokens via the `resource` parameter, HTTPS-only endpoints/redirects, secure token storage, and strict no-token-passthrough; adapt your token store, JWKS, and trust policy to host; omit nothing here — these are hard requirements for any secure MCP auth implementation.

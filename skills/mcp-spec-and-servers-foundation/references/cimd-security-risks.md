<!-- capsule-v2 -->
# CIMD Security Risks — what does an authorization server fetching client metadata from an arbitrary URL have to defend against, and how?

**Source:** modelcontextprotocol/specification MIT `main@57ac4a2e`; Codebase Memory `modelcontextprotocol`. **Question:** What is the complete risk taxonomy of Client ID Metadata Document fetching (impersonation, SSRF, DDoS) and the mandated mitigations at both SEP-991 and the modern spec's security-considerations level?

## Risk taxonomy + mitigation ladder
**Path/Symbol:** `docs/seps/991-enable-url-based-client-registration-using-oauth-c.mdx` (:198–231 risks; :225 localhost warning SHOULD; :287–296 security implications/best practices) × `docs/specification/2026-07-28/basic/authorization/security-considerations.mdx` (:82–105 CIMD security).
**Signature:** server-side: `fetchClientMetadata(client_id_url) -> ClientMetadataDocument | error(invalid_client|invalid_request)` — triggered whenever the AS sees a URL-formatted client_id.
**Data Shape:** three named risks with distinct mitigations:
1. **Localhost URL impersonation** (:200–225): attacker presents the LEGITIMATE client's metadata URL as their own client_id and binds to the same localhost port → intercepts the authorization code after user approval. Detection is hard because "the server sees the correct metadata document and the user sees the correct client name". NOT fully mitigable by CIMD ("same risks as DCR … in a localhost redirect scenario" :223); platform attestation (iOS DeviceCheck / Android Play Integrity consumed by a backend issuing short-lived JWTs usable as `private_key_jwt`) or client-developer JWKS signing services RAISE cost without eliminating it (:212–220).
2. **SSRF** (:227–231): the AS fetches an attacker-chosen URL — a malicious client can make the AS send requests to internal endpoints. Mitigation: "validating the URL's and the IP's those URL's resolve to prior to initiating a fetch request".
3. **DDoS amplification** (:233–237): assessed NON-attractive — request bandwidth ≈ response bandwidth (no amplification) and aggressive AS-side caching kills reuse.

### Decisive source
```md
# sep-991 ...mdx:287–289 + 143–146 (normative core)
Security Implications:
1. Phishing Prevention: Display client hostname prominently
2. SSRF Protection: Validate URLs, limit response size,
   timeout requests, rate limit outbound requests
Best Practices:
- Only fetch client metadata AFTER authenticating the user
- Implement rate limiting on outbound metadata fetches
- Consider additional warnings for new/unknown/localhost domains
- Log metadata fetch failures for monitoring
Server Requirements: Servers SHOULD fetch metadata documents when
encountering URL-formatted client_ids ... cache respecting HTTP
headers (max 24 hours recommended); MUST validate redirect URIs
match those in the metadata document.
```

**Flow:** authorization request arrives with URL-formatted client_id → AS authenticates the user FIRST, then fetches the document → validates (client_id ≡ document URL exactly; redirect_uri ∈ document list; structure valid; optional domain trust policy) → consent page shows `client_name` AND the redirect URI hostname prominently → issues code via redirect. On validation failure respond `error=invalid_client` or `invalid_request`.
**Invariant:** the HTTPS domain hosting the metadata is the trust anchor ("cryptographically binds redirect URIs to the client identity" :192–196 — that binding is the whole point of CIMD vs self-asserted DCR), but it proves NOTHING about who is running on the user's localhost. A porter who skips the user-auth-before-fetch ordering, who fetches without IP/size/timeout/rate guards, who caches beyond HTTP cache headers (~24h recommended), who hides the redirect hostname on the consent screen, or who claims CIMD "prevents impersonation" rather than "raises attack cost" breaks the model.
**Probe:** no runtime tests in the spec repo. Deterministic anchors: modern `security-considerations.mdx` :82–105 normative absorption — ASes MUST consider CIMD draft §6 implications, SHOULD address SSRF per the draft's section, SHOULD display additional warnings for localhost-only redirect URIs, MAY require attestation, MUST clearly display the redirect URI hostname during authorization; MAY enforce domain trust policies (draft §6.4/§6.8). Coverage caveat recorded honestly.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "modelcontextprotocol", name_pattern: "client-id-metadata-document-security|localhost", limit: 10 });
```

## Verdict
Adopt the fetch-time guard set (validate-before-fetch URL+IP allowlisting, response-size cap, timeout, outbound rate limit, fetch-after-user-auth, ≤24h cache honoring HTTP headers) plus prominent hostname display and localhost warnings as a package — they are one contract, not options; adapt trust policy strictness (open vs protected servers) to your deployment; omit platform attestation integration unless your client ships on iOS/Android, and never claim localhost impersonation is solved.

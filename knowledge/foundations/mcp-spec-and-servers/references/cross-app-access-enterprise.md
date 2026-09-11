<!-- capsule-v2 -->
# Cross-App Access (ID-JAG) — how does an MCP client authorize through an enterprise IdP without per-server interactive login?

**Source:** modelcontextprotocol/specification MIT `main@57ac4a2e`; Codebase Memory `modelcontextprotocol`. **Question:** How does SEP-990's enterprise profile chain an IdP identity into an MCP access token, and which trust boundaries must a porter keep intact?

## Enterprise delegation ladder (SEP-990, Final)
**Path/Symbol:** `docs/seps/990-enable-enterprise-idp-policy-controls-during-mcp-o.mdx` (whole; flow sequence :62–93; abstract :37–42; breaking-changes opt-in :48–50).
**Signature:** none — prose-normative extension of the OAuth profile built on OAuth Token Exchange (RFC 8693) and Cross-App Access (draft-ietf-oauth-cross-app-access); the IdP issues an **ID-JAG** (Identity Assertion Authorization Grant / JWT authorization grant), not a normal access token.
**Data Shape:** four actors beyond the usual trio — Browser, MCP Client, MCP Authorization Server (MAS), MCP Resource Server (MRS) — plus the enterprise Identity Provider. The credential that crosses from IdP-world to MAS-world is the ID-JAG; the MAS validates it and mints a standard MCP access token.

### Decisive source
```md
# sep-990 ...mdx:62–93 (sequence, abridged; comments verbatim)
C-->>UA: Redirect to IdP            # phase 1 = ordinary user login AT THE IDP
UA->>IdP: User logs in
IdP-->>C: ID Token                  # "Client stores ID Token"
C->>IdP: Exchange ID Token for ID-JAG
note over IdP: Evaluate Policy      # <-- ENTERPRISE CONTROL POINT
IdP-->>C: Responds with ID-JAG
C->>MAS: Token Request with ID-JAG
note over MAS: Validate ID-JAG      # MAS trusts IdP-issued grant, NOT user creds
MAS-->>C: MCP Access Token
loop C->>MRS: Call MCP API with Access Token → response
```

**Flow:** user logs in once at the enterprise IdP (client stores the ID token) → for EACH MCP server, the client exchanges that ID token at the IdP for an ID-JAG, during which the IdP evaluates enterprise policy (which MCP servers are allowed for this user/org) → the client presents the ID-JAG at the MCP server's authorization server as the grant in its token request → the AS validates the ID-JAG and issues an ordinary MCP access token → API calls proceed normally.
**Invariant:** the IdP is the sole policy authority and the only issuer of grants; the MAS never sees user credentials, only IdP-signed assertions, and must validate the ID-JAG before minting any token. The end-user benefit is single sign-on across ALL organizational MCP servers ("removes the need to manually connect and authorize the MCP Client to individual services"); the admin benefit is centralized allow/deny at the policy-evaluation step. A porter who lets the client cache ID-JAGs across users, who accepts an ID token itself (instead of the exchanged grant) at the token endpoint, or who implements policy checks anywhere other than the IdP breaks the model. Adoption is OPT-IN: this "augments the existing OAuth profile … clients can opt in to this profile when necessary" (:50) — it does not replace the standard flow.
**Probe:** no runtime tests in the spec repo (docs corpus). Deterministic anchors: reference implementation `github.com/oktadev/okta-cross-app-access-mcp` cited in-SEP :46; normative successor text lives in the modern spec's authorization pages (see `authorization-overview`). Coverage caveat recorded honestly.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "modelcontextprotocol", name_pattern: "sep-990|enterprise-idp|cross-app", limit: 10 });
```

## Verdict
Adopt the two-exchange shape (ID token→ID-JAG at the IdP, ID-JAG→access token at the MAS) with policy evaluation living ONLY in the IdP and validation ONLY in the MAS; adapt your IdP's policy engine, grant format, and client session storage to host; omit nothing if you serve enterprise customers — but treat it as an optional profile layered on the standard flow, never the default path for consumer deployments.

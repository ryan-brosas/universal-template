<!-- capsule-v2 -->
# Client-Credentials M2M — how does a machine-to-machine MCP deployment authorize when no end user is available?

**Source:** modelcontextprotocol/specification MIT `main@57ac4a2e`; Codebase Memory `modelcontextprotocol`. **Question:** Which OAuth client-credentials authentication methods does the MCP authorization spec allow for service-to-service (headless) clients, and why only those two?

## Two-method constraint (SEP-1046, Final)
**Path/Symbol:** `docs/seps/1046-support-oauth-client-credentials-flow-in-authoriza.mdx` (whole; specification :45–49; rationale :53–60).
**Signature:** token request with `grant_type=client_credentials` authenticated by exactly one of: (1) **RFC 7523 JWT assertion** (RECOMMENDED) or (2) **client secret via HTTP Basic** (allowed for compatibility). mTLS and everything else are deliberately excluded.
**Data Shape:** the modern GA spec's flow diagram carries this as a first-class branch — `docs/specification/2026-07-28/basic/authorization/index.mdx` :169–171 shows `else Client client registration → C->>A: POST /register` inside the registration alt, while :383–384 of the step-up flow explicitly bifurcates client behavior BY GRANT TYPE: "Clients acting on behalf of a user SHOULD attempt the step-up authorization flow. Clients acting on their own behalf (`client_credentials` clients) MAY attempt the step-up authorization flow or abort the request immediately."

### Decisive source
```md
# sep-1046 ...mdx:55–58 + 60
the specification would RECOMMEND the use of asymmetric methods
defined in RFC 753 [sic; RFC 7523] (JWT Assertions), but also allow
client secrets.
To maximize interoperability (and minimize SDK complexity), this change
would intentionally constrain the client credentials flow to two options:
1. JWT Assertions as per RFC 7523 (RECOMMENDED)
2. Client Secrets via HTTP Basic authentication (Allowed ...)
Other options, such as mTLS, are not included.
... implementers needing to ship solutions ASAP will most likely use
client secrets ... whereas the JWT Assertion pattern represents the
longer-term direction.
```

**Flow:** headless deployment provisions a confidential client at the AS (no browser, no PKCE, no consent screen) → token request `grant_type=client_credentials` with either a signed JWT assertion (asymmetric, longer-term direction) or Basic-auth client secret (maximum legacy compatibility) → AS issues access token (+ optionally refresh per its policy) → client calls the MCP server as itself. The JWT-assertion profile intentionally leaves two holes open pending other IETF work: how to populate the JWT contents (WIMSE Headless JWT Authentication draft) and how the AS discovers the client's JWKS URI to validate it (Client ID Metadata Document's `jwks_uri`) — "intentionally left unspecified … extensibility for these future profiles".
**Invariant:** interoperability over expressiveness — exactly TWO auth methods, no mTLS. A porter who adds mTLS or custom auth methods fragments SDK behavior across implementations; a porter who treats the JWT contents or JWKS discovery as specified builds against moving ground. Step-up semantics differ BY ACTOR: user-delegated clients re-authorize on insufficient-scope, M2M clients may abort instead (re-authorization without a user is often impossible).
**Probe:** no runtime tests in the spec repo. Deterministic anchors: step-up actor split verbatim at modern `authorization/index.mdx` :383–384; SEP status Final. Coverage caveat recorded honestly.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "modelcontextprotocol", name_pattern: "client-credentials|step-up", limit: 10 });
```

## Verdict
Adopt the two-method ladder (JWT assertion recommended target architecture; Basic secret as the shipping-today fallback), the mTLS exclusion, the deliberate non-specification of JWT contents/JWKS discovery until WIMSE+CIMD mature, and the actor-split step-up policy (user clients step up, M2M clients may abort); adapt your provisioning and secret rotation to host; omit interactive-flow machinery (PKCE/consent) from pure M2M paths — but note the spec still defines the baseline and implementations MAY support other authorization scenarios beyond it.

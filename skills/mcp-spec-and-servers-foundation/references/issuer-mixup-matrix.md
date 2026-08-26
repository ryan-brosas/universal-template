<!-- capsule-v2 -->
# Issuer Mix-Up Matrix — how must an MCP client validate the `iss` parameter on authorization responses, and when does absence mean reject vs proceed?

**Source:** modelcontextprotocol/specification MIT `main@57ac4a2e`; Codebase Memory `modelcontextprotocol`. **Question:** What is the exact four-row decision matrix for authorization-response issuer validation, and what comparison/normalization rules make it safe?

## Four-row matrix (SEP-2468 → GA normative)
**Path/Symbol:** `docs/specification/2026-07-28/basic/authorization/index.mdx` :190–213 (Authorization Response Validation; matrix :198–203; third-row rationale :207; no-normalization rule :211; error-response clause :213) × `docs/seps/2468-recommend-issuer-claim-for-auth.mdx` (whole).
**Signature:** `validateIss(iss_param?: string, recorded_issuer: string, advertised: boolean) -> ok | REJECT` — recorded_issuer MUST come from the AS metadata document already validated for issuer≡URL identity (see `authorization-server-discovery`) and be stored in the SAME per-request record as the PKCE verifier and `state`.
**Data Shape:**

| `authorization_response_iss_parameter_supported` | `iss` in response | Client action |
|---|---|---|
| `true` | present | Compare to recorded issuer, simple string comparison (RFC 3986 §6.2.1) |
| `true` | absent | **Reject the response** |
| `false` or absent | present | Compare to recorded issuer (simple string comparison) |
| `false` or absent | absent | Proceed |

### Decisive source
```md
# index.mdx :207 + :211 + :213
The third row applies the local-policy provision in RFC9207 §2.4:
this specification compares a present iss against the recorded
issuer REGARDLESS of metadata advertisement, to accommodate
authorization servers that emit iss before updating their metadata.
...
clients MUST NOT apply scheme or host case folding, default-port
elision, trailing-slash, or percent-encoding normalization
(RFC 3986 §§6.2.2–6.2.3) before comparison.
...
This validation applies equally to error responses — on mismatch
the client MUST NOT act on or display `error`, `error_description`,
or `error_uri`.
```

**Flow:** before redirecting the user-agent the client records the expected `issuer` from validated AS metadata into its per-request state alongside PKCE verifier/state → user authorizes → callback arrives with `code` (+ maybe `iss`) → client decodes `iss` from the form-urlencoded response and applies the matrix BEFORE transmitting the code anywhere → mismatch ⇒ abort the flow entirely (and on a mismatched ERROR response, never surface or act on the error fields — they come from the attacker).
**Invariant:** compare-don't-discard is a DELIBERATE deviation from RFC 9207 §2.4's SHOULD-discard: SEP-2468's rationale (:88–90) is that discarding would reject legitimate flows in the window where an AS emits `iss` before flipping its metadata flag, while rejection-on-mismatch stays unconditional so nothing is relaxed — the recorded baseline was already authenticated per RFC 8414 §3.3. A porter who "fixes" the comparison with URL normalization (case folding / port elision / trailing slash) reopens mix-up via equivalent-URL confusion; a porter who validates AFTER redeeming the code leaks it to a hostile AS; a porter who trusts an expected-issuer from any unvalidated source gets zero protection ("provides no protection if the expected issuer was obtained from an unvalidated source" :192).
**Probe:** no runtime tests in the spec repo. Deterministic anchors: reference implementations cited in SEP-2468 :100–105 — Go SDK PR #859 and TypeScript SDK PR #1957 "record the expected issuer before redirect and compare any received `iss`, rejecting on absence only when the server advertises support"; SDK consequence documented at :94 — hosts whose callback handlers don't extract `iss` will have flows rejected until they widen signatures. Coverage caveat recorded honestly.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "modelcontextprotocol", name_pattern: "authorization-response-validation|mix-up", limit: 10 });
```

## Verdict
Adopt the matrix verbatim including the third-row compare-even-if-unadvertised policy, byte-exact string comparison with NO URL normalization, validate-before-code-redemption ordering, shared per-request storage with PKCE verifier/state, and the don't-display-error-fields-on-mismatch rule; adapt your callback signature to thread `iss` (SDKs widen additively); omit discard-on-unadvertised behavior — the spec chose comparison instead, keyed future-MUST upgrade awareness (`iss` SHOULD→MUST transition announced at :209) into your roadmap.

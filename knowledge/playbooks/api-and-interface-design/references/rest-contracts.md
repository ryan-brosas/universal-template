# HTTP/REST contract choices

Use the established protocol and consumer contract. Google resource-oriented APIs,
Azure REST conventions, JSON:API, and framework-native APIs need not share naming,
version placement, or error envelopes.

- Model resources and operations for consumers, not as an automatic database-table
  export. Stable names and standard HTTP methods help where resource semantics fit;
  an explicit command endpoint can be clearer for a domain operation.
- Preserve HTTP method semantics. PUT and DELETE are idempotent in intended effect,
  not necessarily identical response status. PATCH and POST are not automatically
  idempotent. Where clients must retry a mutation, specify deduplication scope,
  request identity, concurrent duplicates, retention, and response recovery. A
  header name alone is not a retry protocol.
- Use status codes and the project's error representation. Stable error codes help
  branching clients; messages serve people. RFC 9457 Problem Details, framework
  responses, and provider-specific formats are alternatives, not fields to combine
  into a new universal envelope. Expose correlation information only where useful
  and safe; do not return secrets, stack traces, or internal paths.
- Authorize access before disclosing protected data. Choose 403 versus a deliberate
  404 concealment response according to resource-disclosure policy and protocol;
  neither status alone proves that existence is hidden. Include timing, list
  endpoints, and other observable differences in the threat model when relevant.
- Paginate potentially growing collections. Cursor/keyset approaches suit changing
  datasets and large scans; bounded offset pagination or a truly bounded unpaginated
  result may suffice. Specify ordering, continuation termination, filters, and
  concurrent changes. Keep cursors opaque; never treat them as authorization.
- Add rate/quota controls when required by capacity, abuse risk, or commercial
  policy. Document enforced limits and the selected protocol's retry signals.
  Do not invent legacy `X-RateLimit-*` headers where no such contract exists.
- Choose versioning from compatibility needs; see `compatibility.md`. Neither
  `/v1/` nor an `api-version` query parameter is mandatory for every API.

## Retained prior art

These archived `awesome-guidelines` capsules preserve the Azure/Google learning
that previously lived behind `api-design-practices`. They are source-specific
options, not authority over a project's current standard. Recheck current upstream
requirements before claiming conformance to either provider.

- `../../awesome-guidelines/references/api-design-learning-note.md`
- `../../awesome-guidelines/references/api-design-resource-names.md`
- `../../awesome-guidelines/references/api-design-http-idempotency.md`
- `../../awesome-guidelines/references/api-design-errors-machine-readable.md`
- `../../awesome-guidelines/references/api-design-pagination-and-lists.md`
- `../../awesome-guidelines/references/api-design-versioning-contract.md`

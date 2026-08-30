<!-- capsule-v2 -->
# Dual-era server dispatch — how does ONE server process serve both stateless-modern and initialize-handshake clients?

**Source:** modelcontextprotocol/specification MIT `main@4df2d6b6e3588efb46e7542d98498e5c630a0a86`; Codebase Memory `modelcontextprotocol`. **Question:** When a server must accept both modern (`_meta`-per-request) and legacy (`initialize` handshake) clients, how does it select semantics per connection without mixing eras?

## Era selection from the client's opening move
**Path/Symbol:** `docs/specification/2026-07-28/basic/versioning.mdx` (:29–39 terminology; :126–152 backward-compat detection; :159–172 compatibility matrix; :174–183 dual-era dispatch rules).

**Signature:** dual-era server dispatch = pure function of the first request observed: `params._meta` carrying required `io.modelcontextprotocol/*` keys ⇒ serve **stateless modern** under this revision; method `"initialize"` ⇒ select **legacy semantics** scoped to the stdio process or the HTTP session negotiated by that handshake.

**Data Shape:** no configuration flag decides the era — the request shape does. Modern requests carry `_meta.protocolVersion` + `_meta.clientCapabilities` (see `modern-era-lifecycle`); legacy requests carry neither and open with `initialize`.

### Decisive source
```md
# docs/specification/2026-07-28/basic/versioning.mdx:174-183
A dual-era **server** selects its behavior from how the client opens:

- A request carrying modern per-request `_meta` is served statelessly
  according to this revision.
- An `initialize` request selects legacy semantics, scoped to the stdio
  process (stdio) or the session (HTTP), as specified by the negotiated
  legacy protocol version.

A dual-era server **MAY** serve both eras concurrently on the same endpoint
or process.
```

**Flow:** client opens → modern-shaped request? serve stateless (every request independently validated) : `initialize` received? negotiate legacy revision and scope all subsequent state to that process/session. Failure matrix (:166–171): Modern-client→Legacy-server FAILS non-deterministically ("implementation-defined error, stay silent, or even process an era-ambiguous method under legacy semantics") — which is why clients SHOULD probe with `server/discover` first on stdio; Legacy-client→Modern-server fails deterministically (JSON-RPC error / HTTP 400). A recognized modern JSON-RPC error in any failure response identifies a MODERN server → retry with advertised versions, NEVER fall back (:143–146).

**Invariant:** era is a property of the SERVER PROCESS/ORIGIN, not of individual requests — clients cache it for the server lifetime and MAY persist across restarts, re-probing if the assumption breaks (:148–152). A porter who re-detects the era per-request, or who lets a modern request mutate legacy-session state (or vice versa), corrupts the other era's clients. Legacy-only clients have NO fall-forward mechanism: a modern-only server rejecting `initialize` SHOULD name its supported versions in the error message — that error may be the only diagnostic the legacy client can surface (:154–157).

**Probe:** no runtime test suite in the spec repo; machine-checkable anchors are `UnsupportedProtocolVersionError` (-32022, `{supported:[], requested}` data) in `schema/draft/schema.ts` and the transport binding pages' backward-compatibility sections (stdio probe rules, streamable-http 400-body inspection — both cited in their transport capsules). Coverage caveat recorded honestly.

## Get live surrounding code
**Retrieve:** (`query` BM25 now zero-hits this doc-shaped graph — noise-label filtering; use `name_pattern` over the era-dispatch identifiers):
```bash
codebase-memory-mcp cli search_graph --project modelcontextprotocol \
  --name-pattern 'UnsupportedProtocolVersion|DiscoverResult' --limit 10
```

## Verdict
Adopt opening-move era dispatch (request shape decides, concurrent eras allowed), client-side era caching per server process/origin, and the supported-versions-in-error courtesy for legacy clients; adapt the probe cadence and persistence of the cached era to your host's restart model; omit per-request era re-detection (breaks the invariant) and omit legacy support entirely if your client population is modern-only.

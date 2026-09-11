<!-- capsule-v2 -->
# Modern-era stateless lifecycle — how do version, identity, and capabilities reach the server without an initialize handshake?

**Source:** modelcontextprotocol/specification MIT `main@4df2d6b6e3588efb46e7542d98498e5c630a0a86`; Codebase Memory `modelcontextprotocol`. **Question:** What must every request carry so a server processes it with zero session state, and what are the exact rejection codes when it doesn't?

## Per-request `_meta` is the whole handshake
**Path/Symbol:** `schema/draft/schema.ts` (`RequestMetaObject` :63–111 — required `io.modelcontextprotocol/protocolVersion` + required `io.modelcontextprotocol/clientCapabilities`, optional `clientInfo`, deprecated `logLevel`; `ResultMetaObject.serverInfo` :143–158; `NotificationMetaObject."io.modelcontextprotocol/subscriptionId"` :120–134; reserved-key rules `MetaObject` :54 + basic/index.mdx :330–357); prose: `docs/specification/draft/basic/index.mdx` (Statelessness :182–219, per-request fields table :365–393), `docs/specification/draft/basic/versioning.mdx` (:41–78 negotiation).

**Signature:** every client request's `params._meta: RequestMetaObject` — `"io.modelcontextprotocol/protocolVersion": string` (REQUIRED, e.g. `"2026-07-28"`), `"io.modelcontextprotocol/clientCapabilities": ClientCapabilities` (REQUIRED; `{}` = no optional capabilities), `"io.modelcontextprotocol/clientInfo"?: Implementation`.

### Decisive source
```md
# docs/specification/draft/basic/index.mdx:380-392
A request missing any required field is malformed; the server MUST reject it
with JSON-RPC error code -32602 (Invalid params). On HTTP, the response status
MUST be 400 Bad Request.
...
A server MUST NOT rely on capabilities the client has not declared. If
processing a request requires a capability the client did not include in
"io.modelcontextprotocol/clientCapabilities", the server MUST return a
MissingRequiredClientCapabilityError (-32021) whose data.requiredCapabilities
lists the missing capabilities.
```
Statelessness rule (:191–202): servers **MUST NOT** rely on prior requests over the same connection to establish context — no capabilities, version, or client identity inferred from history. Cross-request state **MUST** ride an explicit identifier passed on each request.

**Error-code partition** (basic/index.mdx :111–155 + schema.ts :312–450): standard JSON-RPC `-32700/-32600..-32063` as usual; `-32000..-32019` legacy (never allocate); `-32020..-32099` spec-reserved — `-32020 HeaderMismatch`, `-32021 MissingRequiredClientCapability`, `-32022 UnsupportedProtocolVersion`. `-32002` and `-32042` are retired codes this revision MUST NOT emit.

**ResultType polymorphism** (basic/index.mdx :75–85 + schema.ts :216–236): every result carries `resultType`; `"complete"` = final content, `"input_required"` = MRTR retry coming, unknown values are invalid, but clients MUST treat absent `resultType` from older servers as `"complete"`.

**Flow:** client sends any RPC with full `_meta` → server validates presence (`-32602`/HTTP 400 if missing) → checks requested protocolVersion against its supported list → mismatch ⇒ `-32022 UnsupportedProtocolVersionError` with `{supported: [...], requested}` data (versioning.mdx :48–72); client picks a mutually supported version and retries, or calls `server/discover` first (optional; result = `DiscoverResult{supportedVersions, capabilities, instructions?}`, schema.ts :665–709).

**Era detection** (versioning.mdx :126–183, stdio/streamable-http backward-compat sections): "modern" = per-request metadata (2026-07-28+); "legacy" = initialize handshake (≤2025-11-25). A recognized modern JSON-RPC error in a failure response identifies a modern server — retry, never fall back. Any other error/timeout ⇒ legacy ⇒ fall back to `initialize`. Cache era per server process/origin.

**Invariant:** the server treats EVERY request independently; porters who cache capabilities or version across requests break dual-era correctness and horizontal scaling. Conversely a modern-only client that omits `_meta.protocolVersion` gets hard-rejected by design.

**Probe:** direct tests live in the SDK repos, not the spec repo — the spec repo's machine-checkable contract is `schema/draft/schema.ts` types plus generated JSON Schema (`scripts/generate-schemas.ts` regenerates `schema.json` from these TS types; `scripts/validate-examples.ts` validates every `examples/**.json` referenced via `{@includeCode}` against them). Coverage caveat recorded honestly: no runtime test suite exists here.

## Get live surrounding code
**Retrieve:** (`query` BM25 now zero-hits this doc-shaped graph — Variable/Section nodes are noise-label-filtered by the engine; `name_pattern` is the working primitive):
```bash
codebase-memory-mcp cli search_graph --project modelcontextprotocol \
  --name-pattern 'RequestMetaObject|UnsupportedProtocolVersion|DiscoverResult' --limit 10
# → ~30 rows; e.g. DiscoverResult Variable schema/2026-07-28/schema.json :739-786
```

## Verdict
Adopt per-request `_meta` carrying version+capabilities, the `-320xx` partition, `resultType` polymorphism with absent-means-complete back-compat, and discover-probe era detection; adapt the supported-version list and error message copy to your host; omit the deprecated `logLevel`/logging capability surface unless serving old clients.

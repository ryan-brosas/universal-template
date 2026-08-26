<!-- capsule-v2 -->
# `_meta` key grammar & required request keys — what does every request have to carry, and which `_meta` names are yours to use?

**Source:** modelcontextprotocol/specification MIT `main@4df2d6b6e3588efb46e7542d98498e5c630a0a86`; Codebase Memory `modelcontextprotocol`. **Question:** Which `_meta` keys are protocol-reserved vs extension-owned, what is the exact key grammar, and which keys MUST every request include?

## Reserved keys, two-segment grammar, per-request statelessness
**Path/Symbol:** `schema/draft/schema.ts` — `MetaObject` :34–54 (grammar doc), `RequestMetaObject` :63–111, `NotificationMetaObject` :120–134 (`io.modelcontextprotocol/subscriptionId`), `ResultMetaObject` :143+.
**Signature:** `type MetaObject = Record<string, unknown>` (:54) — the value side is intentionally opaque; all contract lives in key names + documented interfaces extending it.
**Data Shape:** Valid keys have two segments: optional **Prefix** (dot-separated labels ending in `/`; labels start with a letter, end letter-or-digit, interior letters/digits/hyphens; reverse-DNS RECOMMENDED) + **Name** (empty, or starts/ends `[a-zA-Z0-9]` with interior alnum/`-`/`_`/`.`).

### Decisive source
```ts
// schema/draft/schema.ts:45 — the reservation rule a porter WILL get wrong:
//   Any prefix where the second label is `modelcontextprotocol` or `mcp` is
//   **reserved** for MCP use. For example: `io.modelcontextprotocol/`,
//   `dev.mcp/`, `org.modelcontextprotocol.api/`, and `com.mcp.tools/` are all
//   reserved. However, `com.example.mcp/` is NOT reserved, as the second label
//   is `example`.
// :76-98 — the three request-carried reserved keys:
"io.modelcontextprotocol/protocolVersion": string;   // Required. HTTP: MUST equal
  // the MCP-Protocol-Version header, else 400 Bad Request; unsupported version =>
  // UnsupportedProtocolVersionError.
"io.modelcontextprotocol/clientInfo"?: Implementation; // Self-reported, NOT verified;
  // servers SHOULD NOT change behavior or make security decisions on it.
"io.modelcontextprotocol/clientCapabilities": ClientCapabilities; // Required.
  // Declared PER REQUEST rather than once at initialization; an empty object
  // means the client supports no optional capabilities. Servers MUST NOT infer
  // capabilities from prior requests.
```

**Flow:** every request (list/call/read/discover) → carries `_meta` with `protocolVersion` (required, header-cross-checked on HTTP) + `clientCapabilities` (required, fresh each time) → optional `clientInfo` (display/log/debug only) → optional `logLevel` (logging opt-in, see logging-stream-contract) → notifications may carry `subscriptionId` when delivered on a listen stream.
**Invariant:** capability and identity state is PER-REQUEST — a porter who caches capabilities from an earlier request breaks the modern-era stateless contract (this is what makes servers stateless between requests); extension data MUST live under your own prefixed keys (`com.yourco/…`), never bare names, and never under a second-label `modelcontextprotocol`/`mcp` prefix.
**Probe:** no runtime tests in the spec repo; machine anchors are the TS interfaces themselves plus `scripts/generate-schemas.ts` → `schema.json` and `scripts/validate-examples.ts`. Coverage caveat recorded honestly; `docs/specification/draft/basic/lifecycle.mdx` used as secondary context only (coverage freshness reported `missing`).

## Get live surrounding code
**Retrieve:** (`query` BM25 now zero-hits this doc-shaped graph — noise-label filtering; use `name_pattern`):
```bash
codebase-memory-mcp cli search_graph --project modelcontextprotocol \
  --name-pattern 'MetaObject|protocolVersion|clientCapabilities' --limit 10
```

## Verdict
Adopt the two-segment key grammar, the second-label reservation rule, and per-request `protocolVersion`/`clientCapabilities` carriage; adapt your own extension namespace (reverse-DNS prefix); omit assumptions that `clientInfo` is trustworthy — treat it as UI/logging decoration only.

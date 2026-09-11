<!-- capsule-v2 -->
# Case-sensitive key encoding — how do you store `Foo` and `foo` on one domain when every lookup path lowercases?

**Source:** dub AGPL-3.0-or-later `main@873edc5a`; Codebase Memory `dub`. **Question:** How does dub support case-sensitive short domains without changing its case-insensitive storage/lookup convention?

## XOR+base64 key codec gated by a domain allowlist
**Path/Symbol:** `apps/web/lib/api/links/case-sensitivity.ts:encodeKey/decodeKey/isCaseSensitiveDomain/encodeKeyIfCaseSensitive/decodeKeyIfCaseSensitive/decodeLinkIfCaseSensitive` (1-88); consumers: create-link.ts:49, update-link.ts:76, get-link-or-throw.ts:60, record-link.ts:53, transform-link via decodeLinkIfCaseSensitive.
**Signature:** `encodeKey(text: string): string` / `decodeKey(hash: string): string`; gates return the input unchanged for normal domains.
**Data Shape:** stored key = base64(XOR(key, repeating 32-char constant)) — reversible, deterministic, and (critically) COLLISION-FREE between different casings.

### Decisive source
```ts
// This is not actually a secret key, it's just a string that we XOR with the key to make it case sensitive
const XOR_SECRET_KEY = "58ff90c0dc372ded858cbf8fb2306066";
export const CASE_SENSITIVE_DOMAINS = ["biltapp.link", "buff.ly", /* ... */];

export const encodeKey = (text) =>
  Buffer.from(text.split("").map((char, i) =>
    String.fromCharCode(char.charCodeAt(0) ^ XOR_SECRET_KEY.charCodeAt(i % XOR_SECRET_KEY.length)),
  ).join("")).toString("base64");

// every write path:
key = encodeKeyIfCaseSensitive({ domain: link.domain, key });   // BEFORE prisma write

// every read path (redirect edge + API):
const key = decodeKeyIfCaseSensitive({ domain, key });          // BEFORE prisma lookup
// whole-row variant used at API serialization:
link = skipDecodeKey ? link : decodeLinkIfCaseSensitive(link);  // also rebuilds shortLink
```

**Flow:** domain in `CASE_SENSITIVE_DOMAINS`? → yes: keys are XOR-encoded into an opaque ascii-safe token that preserves case distinctions (`Foo` ≠ `foo` after encoding), written encoded, looked up encoded-from-user-input, and decoded only at API serialization; no: raw key flows through unchanged everywhere. `decodeLinkIfCaseSensitive` decodes the row's key AND re-derives `shortLink`, with `_root` mapping to no path suffix.
**Invariant:** The DB NEVER stores two rows differing only by case on normal domains (MySQL collation folds them); instead of migrating the schema, dub ENCODES the rare case-sensitive domains into a keyspace where distinct inputs are always distinct tokens. The gate is per-domain, so the SAME code serves both regimes — but every touchpoint must use the IfCaseSensitive wrapper (miss ONE lookup path and those domains 404). Encoding is explicitly NOT security (source comment says so): it's a keyspace transform. The redirect edge and the analytics ingestion (`record-link.ts` decodeKey before Tinybird) must agree on the same transform or stats split across ghost links.
**Probe:** no direct unit test (coverage caveat; behavior exercised via integration suites on default domains where the codec is identity). Deterministic probe: `decodeKey(encodeKey("Buff"))` === `"Buff"`; `encodeKey("Foo") !== encodeKey("foo")`; `isCaseSensitiveDomain("dub.sh") === false` ⇒ passthrough.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "encodeKeyIfCaseSensitive decodeKey XOR_SECRET_KEY", limit: 5 });
// → case-sensitivity.decodeKey @ 30-44 · encodeKeyIfCaseSensitive @ 52-60
```

## Verdict
Adopt the reversible per-domain keyspace transform when a legacy case-folding store must serve case-sensitive identifiers — cheaper than schema migration, but wrap EVERY read/write path. Adapt the transform (XOR/base64 → any injective ascii-safe encoding) and the allowlist source. Omit if your store already preserves case.

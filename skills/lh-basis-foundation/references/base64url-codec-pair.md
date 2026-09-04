<!-- capsule-v2 -->
# Base64url codec pair — What does a lossless-looking base64url encode/decode pair hide about padding asymmetry?

**Source:** Linked Helper v2.130.5 ingest (proprietary — citations-only), pin `?@?`; Codebase Memory `lh-basis` @ gen 2026-08-23T00:11:49Z. **Question:** how does the kernel convert between base64url (LinkedIn id surface) and base64 (Buffer decode surface), and is the round-trip actually symmetric?

## Two one-line transforms with asymmetric padding handling
**Path/Symbol:** `core/public-methods/models/helpers/utils/strings.js` — `getBase64FromBase64URL` (7–12), `getBase64URLFromBase64` (13–15).
**Signature:** `getBase64FromBase64URL(base64URLString): string`; `getBase64URLFromBase64(base64String): string`.
**Data Shape:** decode direction = charset swap (`-`→`+`, `_`→`/`) plus re-padding with `'='` repeated `4 - len % 4`; encode direction = inverse charset swap plus STRIPPING all `=`.

### Decisive source
```js
function getBase64FromBase64URL(base64URLString) {
    const paddingLength = 4 - (base64URLString.length % 4);
    const padding = '='.repeat(paddingLength);
    const replacedBase64URLChars = base64URLString.replace(/-/g, '+').replace(/_/g, '/');
    return `${replacedBase64URLChars}${padding}`;
}
function getBase64URLFromBase64(base64String) {
    return base64String.replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '');
}
```

**Flow:** decode: url-safe → standard charset, then unconditionally append padding computed from input length; the result feeds `Buffer.from(x,'base64')` in `Hash.extractExistingMemberId`. encode: standard → url-safe, drop padding entirely.
**Invariant:** the pair is NOT an exact mathematical inverse — probe-verified round-trip: `getBase64URLFromBase64('a+b/c==')` = `'a-b_c'` (5 chars), then `getBase64FromBase64URL('a-b_c')` = `'a+b/c==='` (padding formula yields 3 because `5 % 4 === 1`). The formula assumes canonical lengths (len % 4 ∈ {0,2,3}); a length ≡ 1 input (invalid as base64 anyway) gets over-padded, and Node's forgiving Buffer decoder still accepts it. Safe usage contract: decode only strings that passed `isValidHashString` (fixed length 39), and treat the encoder as "produce a url-safe id", never as half of a guaranteed identity.
**Probe:** executed against dist module:
```bash
node -e "const s=require('<root>/core/public-methods/models/helpers/utils/strings.js');const enc=s.getBase64URLFromBase64('a+b/c==');console.log(enc,'|',s.getBase64FromBase64URL(enc),'|',s.getBase64FromBase64URL('a-b_c'))"
```
→ observed `a-b_c | a+b/c=== | a+b/c===`.
**Retrieve (executed pass 5):**
```ts
await mcp.codebase_memory.trace_path({ project: "lh-basis", function_name: "getBase64URLFromBase64", direction: "inbound" });
```
→ observed `callers_total: 0` in the indexed surface — the encode direction currently has no indexed consumer; the decode direction's sole indexed consumer is `Hash.extractExistingMemberId`.

## Verdict
Adopt the charset-swap codec when your ids must survive URL/cookie surfaces but your binary tooling speaks standard base64; re-pad at DECODE time and strip at ENCODE time exactly like this pair. Adapt alphabet to your transport. Do NOT adopt the assumption that encode(decode(x)) or decode(encode(x)) is byte-stable for non-canonical lengths — gate decoding behind a strict length/charset validator as the kernel does. Coverage: file fully indexed (`no_recorded_issue` @ gen 2026-08-23T00:11:49Z); probe executed against shipped dist module (no test runner in ingest — standing block).

Cross-references: hash-to-member-id-decoding (the validated decode consumer; this capsule owns both codec directions).

<!-- capsule-v2 -->
# Asset chunk wire negotiation — how do you evolve a binary-over-JSON wire format without breaking old peers?

**Source:** strapi MIT Expat (non-EE) `develop@1fd9d80ad5f0a2c97d09ce7529f5cd9fdb91ca2d`; Codebase Memory `strapi`. **Question:** Binary asset chunks must cross a JSON WebSocket; the preferred encoding (base64 string) breaks pre-#23479 peers that do `Buffer.from(item.data.data)` on the legacy `Buffer.toJSON()` shape. How do you ship both shapes and let each peer pick the one it can decode?

## Chunk codec + init-echo seam
**Path/Symbol:** `packages/core/data-transfer/src/utils/transfer-asset-chunk.ts:createTransferAssetStreamChunk` (5–22), `createTransferAssetStreamChunkLegacy` (37–55), `decodeTransferAssetStreamItem` (58–66), `decodeTransferAssetStreamData` (95–117), `transferAssetStreamChunkByteLength` (120–145); negotiation point `packages/core/data-transfer/src/strapi/remote/handlers/push.ts:init` (528–574, echo at 566–572); client fallback in `packages/core/data-transfer/src/strapi/providers/remote-destination/index.ts` (init response handling).
**Signature:** `createTransferAssetStreamChunk(assetID, chunk: Buffer | Uint8Array): {action:'stream', assetID, encoding:'base64', data:string}`; `decodeTransferAssetStreamData(data: unknown, encoding?: 'base64'): Buffer`.
**Data Shape:** three accepted payload shapes after `JSON.parse`: (1) base64 STRING with `encoding:'base64'` (preferred; keeps JSON.parse heap bounded), (2) legacy `{type:'Buffer', data:number[]|TypedArray}` from Node's `Buffer.toJSON()` (~6× larger on the wire and allocates the full byte array during parse — what #23479 fixed for large files), (3) in-process `Buffer` instance.

### Decisive source
```ts
// decode ladder — receivers accept ALL shapes; flags and payload may disagree without throwing
export function decodeTransferAssetStreamData(data: unknown, encoding?: 'base64'): Buffer {
  if (encoding === 'base64' && typeof data === 'string') {
    return Buffer.from(data, 'base64');
  }
  // `encoding: 'base64'` with a non-string payload (or no encoding) uses the same fallbacks as
  // legacy peers — avoids throwing when flags and payload disagree.
  if (Buffer.isBuffer(data)) { return Buffer.from(data); }
  const legacyBufferData = getLegacyBufferJsonData(data);   // {type:'Buffer', data:[...]}
  if (legacyBufferData) { return Buffer.from(legacyBufferData); }
  if (typeof data === 'string') { return Buffer.from(data, 'base64'); }
  throw new TypeError('Invalid transfer asset stream chunk payload');
}
```
```ts
// push.ts init — capability is negotiated by ECHO: server returns assetEncoding only if it
// can decode it; older remotes never echo, so the client falls back to the legacy shape
return {
  transferID,
  checksums: true,
  ...(params?.assetEncoding === 'base64' ? { assetEncoding: 'base64' as const } : {}),
};
```
```ts
// encoders refuse null chunks up front — the failure mode they prevent is
// Buffer.from(undefined) on the receiving side
if (chunk == null) {
  throw new TypeError('Asset stream yielded a null/undefined chunk; refusing to encode (would trigger Buffer.from(undefined))');
}
```

**Flow:** client requests `assetEncoding:'base64'` in the `init` command → server echoes the field only when its decoder supports it (and always echoes `checksums:true`) → client inspects the init response: echoed ⇒ send `{encoding:'base64', data:<string>}` chunks; not echoed (pre-#23479 remote) ⇒ send legacy `buffer.toJSON()` chunks → every receiver runs every chunk through the same decode ladder regardless of which shape arrived → checksums are negotiated by the identical echo pattern (`checksums:true` in params, echoed back; a peer that does not support negotiation gets a warning diagnostic and end items WITHOUT a checksum field).
**Invariant:** the decoder must accept the union of all historically-shipped shapes — a receiver that only accepts the newest shape turns a version skew into a hard crash instead of a slow transfer; the echo is the ONLY capability signal (no version numbers on the wire), so "field absent" must mean "unsupported", never "unknown"; encoders fail fast on null/undefined chunks because the remote failure (`Buffer.from(undefined)`) is unattributable; the byte-length estimator (`transferAssetStreamChunkByteLength`) must agree with the encoder's actual wire size per shape or client-side batching (1MiB flush threshold) miscounts.
**Probe:** `src/utils/__tests__/transfer-asset-chunk.test.ts` (170 lines, whole) — round-trip, legacy-shape decode, Buffer-instance decode, base64-without-flag decode, and the Node-`toJSON` wire-compatibility test proving a raw Buffer property stringifies to the legacy shape even through the WS replacer; `src/strapi/providers/remote-destination/__tests__/asset-encoding-negotiation.test.ts` (non-echoing init response ⇒ legacy shape on the wire); `checksum-negotiation.test.ts` (whole: unsupported peer ⇒ warning + `endItem.checksum` undefined); `push-assets-write-stream.test.ts` (decoded payload flushed before asset completes when it exceeds 1MiB).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "strapi", query: "createTransferAssetStreamChunk decodeTransferAssetStreamData assetEncoding", file_pattern: "packages/core/data-transfer/src/*", limit: 10, fields: ["signature", "name", "file"] });
```
Pass 4 note: Codebase Memory MCP was not connected in this session; the cited ranges were confirmed by direct read of the checkout at the pinned HEAD instead (see verification.md).

## Verdict
Adopt the pattern generally: negotiate capabilities by echoing requested fields in an init handshake (absent = unsupported), keep a decode ladder that accepts every historical shape, and fail fast at encode time on inputs whose remote failure would be unattributable. This is the portable answer to "evolve a binary-over-text protocol with mixed-version peers". Adapt the concrete shapes (base64 vs your framing) and the 1MiB batch threshold. Omit Strapi's specific #23479 legacy path once your oldest supported peer is newer than it. Coverage caveat: the client-side fallback branch in remote-destination/index.ts is pinned by the negotiation test but the server-side echo line itself has no dedicated unit test.

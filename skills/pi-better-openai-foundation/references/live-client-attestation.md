<!-- capsule-v2 -->
# Client DeviceCheck attestation — how do you build the CBOR client-attestation blob a backend expects without a CBOR library?

**Source:** pi-better-openai MIT `main@86814e9047996abba08e4c907e23286329196fe0`; Codebase Memory `pi-better-openai`. **Question:** How is the `v1.{...}` attestation token assembled (CBOR headers, signal map, failure codes, latency) and when is it omitted entirely?

## Attestation builder
**Path/Symbol:** `src/live/attestation.ts` whole; header encoder `cborHeader` :6-23; signals map :40-54; envelope :56-73; gate `generateCodexAttestation` :75-86.
**Signature:** `generateCodexAttestation(native): Promise<string | undefined>`.
**Data Shape:** Output `` `v1.${base64url(cborMap)}` `` wrapped as JSON `{"v":1,"s":0,"t":...}`; map keys `token`|`error_code`, `bundle_id`, `f` (signals), `t` (latency f64).

### Decisive source
```ts
if (!Number.isSafeInteger(value) || value < 0) throw new Error(...);
if (value < 24)        return Buffer.from([major + value]);          // tiny
if (value <= 0xff)     return Buffer.from([major + 24, value]);
if (value <= 0xffff)   /* major+25 + u16BE */ ;
if (value <= 0xffff_ffff) /* major+26 + u32BE */ ;
throw new Error("CBOR length is too large");

export async function generateCodexAttestation(native) {
  if (process.platform !== "darwin" || process.arch !== "arm64") return undefined; // omit
  try { result = await native.deviceCheckGenerateToken(); } catch { return undefined; }
  return JSON.stringify({ v: 1, s: 0, t: buildClientAttestation(result) });
}
```
Failure honesty (:56-62): unsupported platform/native failure becomes `error_code` 3|4 INSIDE the map — absence of a token is reported as data, never faked. Signals include locale/timezone (clamped ≤64 chars), a per-process random APP_SESSION_ID, and fixed 0/1 pairs; latency encoded as CBOR double `0xfb` prefix when finite.

**Flow:** darwin-arm64 gate → native token attempt → build map (token-or-error_code, bundle, signals, latency) → CBOR-encode → base64url → v1 JSON envelope; ANY failure path yields `undefined` and callers simply send no attestation header.
**Invariant:** The attestation is best-effort by contract: missing native, throw, or non-darwin-arm64 all degrade to `undefined` — the signaling request proceeds WITHOUT it rather than failing; error_code distinguishes unsupported(3) vs failed(4).
**Probe:** `tests/live-native.test.ts` pins the binding validation feeding it; direct attestation-bytes spec absent at this pin — caveat recorded (deterministic source-pin only).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-better-openai", query: "generateCodexAttestation cborHeader buildClientAttestation", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt hand-rolled minimal CBOR + honest error-code fallbacks + platform gate. Adapt bundle id/signal fields to your backend's schema. Omit Apple DeviceCheck specifics outside Apple hosts.

<!-- capsule-v2 -->
# Magic-byte media sniffing — how do you detect a file's IANA type from bytes or base64 without decoding the whole input, and why is audio/mp4 deliberately excluded from generic detection?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory `ai`. **Question:** What is the signature-table design (prefix masks, ID3 skipping, base64 parity), and which container ambiguity did the authors resolve by omission?

## detectMediaType + signature tables
**Path/Symbol:** `packages/provider-utils/src/detect-media-type.ts:detectMediaType` (:283-311), `detectMediaTypeBySignatures` (:235-262), `decodePrefix` (:199-210), `stripID3` (:221-228), tables :3-180.
**Signature:** `detectMediaType({data: Uint8Array | string, topLevelType?: string}): string | undefined`; also `getTopLevelMediaType(mediaType): string` (:324-327) and `isFullMediaType` (rejects `image`, `image/`, `image/*`) (:341-348).
**Data Shape:** Signature = `{mediaType, bytesPrefix: Array<number | null>}` — `null` = wildcard byte. Tables cover image (GIF/PNG/JPEG/WebP/BMP/TIFF×2/AVIF/HEIC), document (%PDF), audio (MP3 sync words ×6/WAV/OGG/FLAC/AAC/WebM + mp4 SEPARATELY), video (mp4/WebM/quicktime/AVI-as-RIFF). `DEFAULT_SNIFF_BYTES = 18`, `MAX_SIGNATURE_BYTES = 12`, `MAX_ID3_TAG_BYTES = 128 * 1024` (exported for boundary tests).

### Decisive source
```ts
// base64 path decodes only ceil(maxBytes/3)*4 chars — same visible prefix as raw bytes:
const maxChars = Math.ceil(maxBytes / 3) * 4;
const bytes = convertBase64ToUint8Array(data.substring(0, Math.min(data.length, maxChars)));
return bytes.length > maxBytes ? bytes.subarray(0, maxBytes) : bytes;
```
```ts
if (hasID3(bytes)) {
  // MP3 frames live AFTER a potentially huge ID3v2 tag; re-decode a bounded
  // 128KiB+12 window past it instead of decoding whole attachments:
  bytes = stripID3(decodePrefix(data, ID3_SCAN_BYTES));
}
```
```ts
// generic detection EXCLUDES the audio/mp4 entry:
...imageMediaTypeSignatures, ...documentMediaTypeSignatures,
// MP4 containers cannot be distinguished as audio or video by ftyp alone.
// Preserve the generic detection result as video/mp4.
...audioMediaTypeSignaturesWithoutMp4,
...videoMediaTypeSignatures,
```

**Flow:** decode ≤18-byte prefix (representation-independent) → optional bounded ID3 strip → first-matching-prefix wins → undefined when nothing matches or topLevelType unsupported (`"text"` ⇒ undefined by table lookup miss).
**Invariant:** Detection results must be IDENTICAL for raw bytes vs base64 of the same file — that parity is what lets callers sniff before choosing a decode strategy; it is achieved by decoding whole 4-char base64 groups then trimming, never mid-group. The audio/video mp4 ambiguity is resolved by CONVENTION (generic sniffer reports video/mp4; only `topLevelType:'audio'` requests can return audio/mp4) — porters who "fix" this by adding audio/mp4 to the generic table break every generic call site. RIFF appears under THREE media types (WebP at 12 bytes with wildcards, WAV at 12, AVI at 4) — match ORDER in the per-type tables is what disambiguates.
**Probe:** `packages/provider-utils/src/detect-media-type.test.ts:135/:163` ("NOT detect RIFF audio as WebP" negative ×bytes/base64), `:328/:364` (ID3-tagged MP3 both representations), `:422/:438` (tag exactly AT vs OVER the 128KiB scan limit — boundary pinned against exported constant), `:510/:519` ("NOT detect WebP as WAV"), plus per-signature bytes/base64 pairs throughout.

## Get live surrounding code
**Retrieve:**
```bash
echo '{"project":"ai","query":"detectMediaType bytesPrefix MAX_ID3_TAG_BYTES stripID3 getTopLevelMediaType","limit":5}' | codebase-memory-mcp cli search_graph
```

## Verdict
Adopt the null-wildcard signature tables, bounded base64 prefix decode, ID3 skip ladder, and the mp4-to-video generic convention verbatim; adapt the table contents to your accepted formats but keep wildcard+order semantics; omit `isFullMediaType` if your host has no allowlist gating on complete subtypes. Extensively direct-test-pinned incl. adversarial negatives and size boundaries at this HEAD.

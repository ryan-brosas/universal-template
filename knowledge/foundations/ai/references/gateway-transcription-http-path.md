<!-- capsule-v2 -->
# Gateway transcription HTTP path + auth-method pre-parse — why does doGenerate base64 audio in the body while doStream derives subprotocols from resolved headers?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory `ai`. **Question:** What does the transcription model's non-streaming half own, and why is authMethod parsed eagerly before the stream starts?

## JSON generate twin of the WS stream
**Path/Symbol:** `packages/gateway/src/gateway-transcription-model.ts:GatewayTranscriptionModel.doGenerate` (52–113) + `getProtocolsFromHeaders` (160–180) + `toGatewayTranscriptionUrl` (155–162).
**Signature:** `async doGenerate({audio, mediaType, providerOptions, headers, abortSignal}): Promise<TranscriptionResult>`; `function getProtocolsFromHeaders(headers): string[]`.
**Data Shape:** POST `{baseURL}/transcription-model` with body `{audio: Uint8Array→base64|string, mediaType, providerOptions?}`; typed response schema (`text, segments[{text,startSecond,endSecond}], language?, durationInSeconds?, warnings discriminated-union[unsupported|compatibility|deprecated|other], providerMetadata`) with `?? []`/`?? undefined` defaults applied client-side. Headers: `ai-transcription-model-specification-version: 4`, `ai-model-id` (NOTE: not `ai-transcription-model-id` — this modality uses the generic id header).

### Decisive source
```ts
audio: audio instanceof Uint8Array ? convertUint8ArrayToBase64(audio) : audio,
// …
const authMethod = await parseAuthMethod(headers);   // BEFORE createGatewayTranscriptionStream
return {
  stream: createGatewayTranscriptionStream({ …, authMethod }),
  request: { body: startFrame },
  response: { timestamp: currentDate, modelId: this.modelId },
};
```
```ts
// Header lookups are case-insensitive because combineHeaders does not normalize casing:
const normalizedHeaders = normalizeHeaders(headers);
const authorization = normalizedHeaders.authorization;
const token = authorization?.startsWith('Bearer ') ? authorization.slice('Bearer '.length) : undefined;
```

**Flow:** doGenerate = single POST → schema-parsed transcript with defaults; doStream = resolve headers → parse authMethod ONCE → build start frame → hand everything to the WS pump with authMethod captured for error conversion later.
**Invariant:** `authMethod` must be parsed BEFORE the async stream begins because WebSocket event handlers are SYNCHRONOUS and cannot await `parseAuthMethod` when converting a late server error to a typed Gateway error. The bearer strip must be case-insensitive on header NAME but exact on the `'Bearer '` VALUE prefix.
**Probe:** `grep -c 'normalizeHeaders(headers)' packages/gateway/src/gateway-transcription-model.ts` → `1`; direct tests: gateway-transcription-model.test.ts 'should base64 encode byte audio in request body' (:143), 'should derive the subprotocols from headers case-insensitively' (:350), 'should default optional transcript fields' (:210).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "GatewayTranscriptionModel doGenerate getProtocolsFromHeaders", limit: 10 });
```
Resolves anchors across `gateway-transcription-model.ts` (whole file indexed).

## Verdict
Adopt the eager-auth-parse pattern for any async-error-conversion-from-sync-callback design; adapt header names; omit nothing — the sync-callback/async-funnel mismatch is the subtle failure this capsule prevents.

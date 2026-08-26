<!-- capsule-v2 -->
# Codex image client — choose generation or edit and decode one safe PNG

**Source:** dsh-codex Apache-2.0 main@e3e54e206f7c829503c7e6eed378643ba0416792; Codebase Memory dsh-codex. **Question:** how should a provider client select the generation versus edit endpoint, authenticate with a refreshable OAuth model, honor cancellation, and fail closed on an image response?

## OpenAICodexImageClient.generate
**Path/Symbol:** src/imagegen.ts:127-195 OpenAICodexImageClient.generate.
**Signature:** generate(prompt: string, images: readonly string[], signal: AbortSignal): Promise<Uint8Array>.
**Data Shape:** The caller supplies a prompt and zero or more already-bounded data URLs. Zero refs select /images/generations; refs select /images/edits. The client returns the first response.data[].b64_json as bytes, never a provider DTO.

### Decisive source
~~~ts
throwIfAborted(signal)
const auth = await abortable(this.models.getAuth(OPENAI_CODEX_PROVIDER), signal)
const access = auth?.auth.apiKey
if (access === undefined || access.length === 0) {
  throw new Error('OpenAI Codex image generation is signed out; run "dsh openai-codex login"')
}
const endpoint = images.length === 0
  ? OPENAI_CODEX_IMAGE_GENERATIONS_URL
  : OPENAI_CODEX_IMAGE_EDITS_URL
const body = {
  ...images.length === 0 ? {} : { images: images.map(image_url => ({ image_url })) },
  prompt,
  background: 'auto',
  model: OPENAI_CODEX_IMAGE_MODEL,
  quality: 'auto',
  size: 'auto',
}
let response: Response
try {
  response = await fetch(endpoint, {
    method: 'POST',
    redirect: 'error',
    headers: {
      authorization: `Bearer ${access}`,
      'chatgpt-account-id': accountIdFromToken(access),
      'content-type': 'application/json',
      accept: 'application/json',
      originator: 'deepseek-harness',
    },
    body: JSON.stringify(body),
    signal,
  })
} catch (error: unknown) {
  throwIfAborted(signal)
  throw new Error('OpenAI Codex image request failed', { cause: error })
}
let payload: unknown
try {
  payload = await response.json()
} catch (error: unknown) {
  throw new Error(`OpenAI Codex returned an unprocessable image response (HTTP ${response.status})`, { cause: error })
}
if (!isRecord(payload) || !Array.isArray(payload['data'])) {
  throw new Error('OpenAI Codex returned an image response without data')
}
const first = payload['data'][0]
if (!isRecord(first) || typeof first['b64_json'] !== 'string' || first['b64_json'].length === 0) {
  throw new Error('OpenAI Codex returned an image response without base64 image data')
}
const encoded = first['b64_json'].trim()
if (!/^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$/u.test(encoded)) {
  throw new Error('OpenAI Codex returned malformed base64 image data')
}
return Buffer.from(encoded, 'base64')
~~~

**Flow:** check the signal before credential work, race model auth against cancellation, derive the account header from the access JWT, choose the endpoint from reference count, post with redirect rejection, parse JSON, map 401/403 to a re-login hint, then validate the envelope and base64 before returning bytes.
**Invariant:** cancellation and signed-out state stop before dispatch; generation/edit selection cannot drift from reference presence; only the first valid base64 image is returned; provider diagnostics are bounded and JWT-redacted, while provider-specific headers and URLs stay inside this client.
**Probe:** tests/imagegen.spec.ts:117-150 (generation endpoint, headers, body, PNG attachment) and 165-180 (edit endpoint/data URL); executed with pnpm test -- tests/imagegen.spec.ts tests/read-image-enhancement.spec.ts tests/tool-policy.spec.ts, yielding 22 test files and 154 tests passed.

## Get live surrounding code
**Retrieve:**
~~~ts
await mcp.codebase_memory.search_graph({ project: 'dsh-codex', qn_pattern: 'dsh-codex\\.src\\.imagegen\\.OpenAICodexImageClient\\.generate', limit: 10, fields: ['signature', 'name', 'file', 'lines'] });
~~~

## Verdict
Adopt the signal-first, endpoint-by-input, bounded-response-decoder shape. Adapt OAuth/account-header and endpoint details to the target provider; keep credential refresh in the host model service. Omit Codex model names and first-party headers when they are not part of the target protocol. Coverage is no_recorded_issue + metadata_match for src/imagegen.ts and tests/imagegen.spec.ts; the direct suite covers successful generation/edit paths, while malformed-provider branches remain source-confirmed.

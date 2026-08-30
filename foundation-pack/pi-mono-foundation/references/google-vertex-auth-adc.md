<!-- capsule-v2 -->
# google-vertex-auth-adc — How do I authenticate a Vertex AI provider across API keys, ADC, and service accounts without misrouting placeholder credentials to the key client?

**Source:** pi-mono (MIT) `main@80e62761f7251a104f1b21d9c73920c720f0ec00`; Codebase Memory `pi-mono`. **Question:** Where is the API-key-vs-ADC fork, which key strings must fall through to ADC, and how do project/location/baseUrl resolve?

## Vertex auth fork inside the stream function
**Path/Symbol:** `packages/ai/src/api/google-vertex.ts` — `stream` :97-111, `resolveApiKey` :425-431, `isPlaceholderApiKey` :433-435, `createClient` :353-369, `createClientWithApiKey` :371-382, `buildGoogleAuthOptions` :420-423, `resolveProject` :437-448, `resolveLocation` :450-456, `buildHttpOptions` :384-401 (`GCP_VERTEX_CREDENTIALS_MARKER` const :58). Consumer credential plane: `packages/ai/src/providers/google-vertex.ts` whole 100L.
**Signature:** `function resolveApiKey(options?: GoogleVertexOptions): string | undefined`; `function createClient(model, project: string, location: string, optionsHeaders?, env?: ProviderEnv): GoogleGenAI`; `function buildGoogleAuthOptions(env?: ProviderEnv): { keyFilename: string } | undefined`.
**Data Shape:** `options.apiKey?: string`, `options.project?/location?: string`, `options.env?: ProviderEnv`; marker string `"gcp-vertex-credentials"`; ADC default path `~/.config/gcloud/application_default_credentials.json` lives in the provider entry (`VERTEX_ADC_PATH`), not the api module.

### Decisive source
```ts
const apiKey = resolveApiKey(options);
// Create the client using either a Vertex API key, if provided, or ADC with project and location
const client = apiKey
    ? createClientWithApiKey(model, apiKey, options?.headers)
    : createClient(model, resolveProject(options), resolveLocation(options), options?.headers, options?.env);

function resolveApiKey(options?: GoogleVertexOptions): string | undefined {
    const apiKey = options?.apiKey?.trim();
    if (!apiKey || apiKey === GCP_VERTEX_CREDENTIALS_MARKER || isPlaceholderApiKey(apiKey)) {
        return undefined;
    }
    return apiKey;
}
function isPlaceholderApiKey(apiKey: string): boolean {
    return /^<[^>]+>$/.test(apiKey);
}
```

**Flow:** stream entry refuses custom fetch ("Custom fetch is not supported by the Google Vertex adapter") → `resolveApiKey` trims and rejects empty / `gcp-vertex-credentials` marker / `<placeholder>` strings ⇒ undefined → ADC branch builds `GoogleGenAI({vertexai:true, project, location, apiVersion:"v1", googleAuthOptions?, httpOptions})` where project = `options.project || GOOGLE_CLOUD_PROJECT || GCLOUD_PROJECT` and location = `options.location || GOOGLE_CLOUD_LOCATION` (each throws an actionable message when missing); real key branch builds `{vertexai:true, apiKey, apiVersion}` without project/location. Provider-entry `resolve()` mirrors this for credential status: stored/`GOOGLE_CLOUD_API_KEY` key wins; else ADC file existence (`credential.env.GOOGLE_APPLICATION_CREDENTIALS ?? env ?? VERTEX_ADC_PATH`) + project + location ⇒ `{auth:{}, env}` (SDK does ADC itself). Login normalizes all THREE methods into `ApiKeyCredential`: api-key stores `key`; adc/service-account store only `env:{GOOGLE_CLOUD_PROJECT, GOOGLE_CLOUD_LOCATION, GOOGLE_APPLICATION_CREDENTIALS?}`.
**Invariant:** A non-key credential shape must never reach `createClientWithApiKey`: marker and `<…>` placeholders are "absent", not secrets; conversely a real key client must NOT carry project/location. `buildGoogleAuthOptions` maps ONLY explicit `GOOGLE_APPLICATION_CREDENTIALS` to `{keyFilename}` — the default ADC path stays the SDK's lookup. Custom baseUrl ⇒ `baseUrlResourceScope: COLLECTION`, and if the URL already contains a `vN(betaN)` path segment set `apiVersion: ""` so versions are never doubled.
**Probe:** `packages/ai/test/google-vertex-api-key-resolution.test.ts` — mocks `@google/genai`, asserts `<authenticated>` and `gcp-vertex-credentials` apiKeys AND `GOOGLE_CLOUD_API_KEY=<authenticated>` all construct `{vertexai:true, project, location, apiVersion:"v1"}` with NO `apiKey` property; real key constructs with `apiKey` and no project/location; custom baseUrl forwarded with `baseUrlResourceScope:"COLLECTION"`; baseUrl already containing `/v1/` gets `apiVersion:""`. Coverage caveat: this suite is BLOCKED at import in the read-only checkout (compat→models.generated→gitignored `data/*.json`; runner exists, fixture needs network `npm run generate-models`); assertions pinned by whole-file direct reads at pin.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-mono", query: "vertex ADC api key client project location placeholder marker", limit: 10, fields: ["signature", "name", "file"] });
```
Live result at pin: `isPlaceholderApiKey` #1 (-35.74), then `resolveLocation`, `createClientWithApiKey`, `resolveProject`, `resolveApiKey`, `createClient` in top 8.

## Verdict
Adopt the two-client fork keyed on sanitized key resolution, the marker/`<placeholder>` veto list, and the per-field project/location env ladders with actionable throws. Adapt credential storage to your host's auth store but keep ADC/service-account creds as env-bearing records so resolution stays side-effect-free. Omit pi's Gemini-3 thinking-budget table if your host has no thinking levels; note Gemini 3 cannot disable thinking (Pro→lowest visible level without includeThoughts, Flash→MINIMAL) if you port it.

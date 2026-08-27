<!-- capsule-v2 -->
# Model-URL pass-through download policy — when should an asset be fetched by the SDK versus handed to the model as a URL?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory `ai`. **Question:** How does the default download function decide per URL, and what contract must a custom download function honor so prompt conversion cannot desync?

## createDefaultDownloadFunction + DownloadFunction
**Path/Symbol:** `packages/ai/src/util/download/download-function.ts:createDefaultDownloadFunction` (:36-45), type `DownloadFunction` (:20-30).
**Signature:** `createDefaultDownloadFunction(download: typeof originalDownload = originalDownload): DownloadFunction` where `DownloadFunction = (options: Array<{url: URL, isUrlSupportedByModel: boolean}>) => PromiseLike<Array<{data: Uint8Array, mediaType: string | undefined} | null>>`.
**Data Shape:** Returns one element PER requested URL, in request order; element is `null` (pass the URL through to the model) or `{data, mediaType}`. A custom function may inject auth/retries or return null to defer.

### Decisive source
```ts
export const createDefaultDownloadFunction =
  (download: typeof originalDownload = originalDownload): DownloadFunction =>
  requestedDownloads =>
    Promise.all(
      requestedDownloads.map(async requestedDownload =>
        requestedDownload.isUrlSupportedByModel
          ? null                       // model fetches it itself — do NOT download
          : await download(requestedDownload),
      ),
    );
```

**Flow:** `convertToLanguageModelPrompt` builds `plannedDownloads` from every file part whose tagged data resolved to `{type:'url'}` (`packages/ai/src/prompt/convert-to-language-model-prompt.ts:506-522`) — `isUrlSupportedByModel` comes from `isUrlSupported({url, mediaType, supportedUrls})` AND requires a known mediaType — then calls `download(plannedDownloads)` in parallel and re-associates results BY INDEX (`plannedDownloads[index].url.toString()` keys the downloadedAssets map, :524-538).
**Invariant:** The result array must be index-aligned with the request array — position is the ONLY correlation channel; any custom implementation that filters/dedupes/reorders breaks asset attribution silently. `null` means "pass through", never "skip": consumers treat null as leave-the-URL-in-the-prompt.
**Probe:** `packages/provider-utils/src/get-from-api.test.ts:31` family pins the consumer side; the pass-through-vs-download branch shape is pinned by `download.test.ts:234` (data URLs never hit fetch) plus the plannedDownloads wiring read at :506-538 (coverage caveat: no dedicated unit test file for download-function.ts itself at this pin — behavior verified via source read + consumer tests).

## Get live surrounding code
**Retrieve:**
```bash
echo '{"project":"ai","query":"createDefaultDownloadFunction isUrlSupportedByModel plannedDownloads downloadableFiles","limit":5}' | codebase-memory-mcp cli search_graph
```

## Verdict
Adopt the boolean-per-request decision protocol with null-as-pass-through semantics and strict order preservation; adapt the support predicate (`isUrlSupported` regex table over mediaType+URL) to your model matrix; omit the parallel `Promise.all` fan-out only if your transport is rate-limited (keep order even when serializing). Coverage caveat recorded: download-function.ts has no own unit file at this pin; pinned indirectly through convert-to-language-model-prompt wiring and download.test.ts.

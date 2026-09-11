<!-- capsule-v2 -->
# SafeFetch SSRF boundary — how do outbound fetches stay SSRF-safe while allowing private-network deployments?

**Source:** Chatwoot MIT `develop@6154aebcfea1fe62e8dd01fbf94568ef827fc51c`; Codebase Memory `ext-chatwoot`. **Question:** How does one HTTP entry point block SSRF by default yet still let self-hosted installs reach intranet webhook targets?

## Facade error taxonomy + private-network escape hatch
**Path/Symbol:** `lib/safe_fetch.rb:SafeFetch.fetch` (lines 26-39) and `.allow_private_network?` (36-38); `lib/safe_fetch/fetcher.rb:SafeFetch::Fetcher#perform_request` (46-50) and `stream_response` rescue list (40-44); `lib/safe_fetch/request_options.rb:SafeFetch::RequestOptions#effective_max_bytes` (38-40).
**Signature:** `SafeFetch.fetch(url, **options) { |result| }` — BLOCK REQUIRED; raises `InvalidUrlError / UnsafeUrlError / FetchError / HttpError / FileTooLargeError / UnsupportedContentTypeError`.
**Data Shape:** Result = `Data.define(:tempfile, :filename, :content_type)`; tempfile is binmode, auto-closed via `close!` in ensure.

### Decisive source
```ruby
def self.fetch(url, **, &)
  raise ArgumentError, 'block required' unless block_given?

  SafeFetch::Fetcher.new(SafeFetch::RequestOptions.new(url: url, **)).fetch(&)
rescue SsrfFilter::InvalidUriScheme, URI::InvalidURIError => e
  raise InvalidUrlError, e.message
rescue SsrfFilter::Error, Resolv::ResolvError => e
  raise UnsafeUrlError, e.message
end

# fetcher.rb — dispatch:
def perform_request(&)
  return SafeFetch::PrivateNetworkRequest.new(options).perform(&) if SafeFetch.allow_private_network?

  SsrfFilter.public_send(options.method, options.url, **options.request_options, &)
end

# env gate:
def self.allow_private_network?
  ActiveModel::Type::Boolean.new.cast(ENV.fetch('SAFE_FETCH_ALLOW_PRIVATE_NETWORK', false))
end
```

**Flow:** every outbound fetch in the app (webhooks, avatar downloads, integrations) goes through SafeFetch → default path delegates to the ssrf_filter gem, which resolves and rejects private/loopback/link-local targets → with `SAFE_FETCH_ALLOW_PRIVATE_NETWORK=true`, a parallel `PrivateNetworkRequest` implementation performs the request directly for self-hosted intranets → response streams chunk-by-chunk into a tempfile with a running byte counter raising `FileTooLargeError` past `effective_max_bytes`; network-layer exceptions are normalized to FetchError so callers handle ONE taxonomy.
**Invariant:** The private-network switch is deployment-level ENV, never per-request — a caller cannot opt a single URL out of SSRF protection; content-type validation is opt-in per call (`validate_content_type: false` on the webhook path) while size capping stays on. Callers MUST pass a block; the result tempfile's lifetime ends when the block returns.
**Probe:** `grep -n 'SAFE_FETCH_ALLOW_PRIVATE_NETWORK' lib/safe_fetch.rb` → line 37; direct test `spec/lib/safe_fetch_spec.rb` pins the facade contract across 43 examples including URL classification and streaming limits.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-chatwoot", query: "SafeFetch fetcher stream tempfile max bytes", limit: 5 });
```
Rank-1: `SafeFetch::Fetcher.with_tempfile lib/safe_fetch/fetcher.rb 24-29`; `stream_response` 31-44 rank-2.

## Verdict
Adopt the single-facade + normalized-error-taxonomy shape and the deployment-level (not call-level) private-network override. Adapt ssrf_filter to your language's equivalent (re-resolve-at-connect anti-DNS-rebinding fetcher) and tempfile policy to your storage layer. Omit the image/video content-type defaults if your fetches aren't attachment-oriented.

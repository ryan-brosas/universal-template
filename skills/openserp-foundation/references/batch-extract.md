<!-- capsule-v2 -->
# Batch extract contract — why does POST /extract/batch return a bare array, and what must never fail the whole batch?

**Source:** OpenSERP MIT `main@29c7b0fb`; Codebase Memory `ext-aeo-openserp`. **Question:** What shape does Open WebUI's ExternalWebLoader require, and where are bad URLs handled?

## handleBatchExtract
**Path/Symbol:** `core/server_extract.go:handleBatchExtract/batchExtractItem/dedupeBatchURLs` (L439–557 end).
**Signature:** `POST /extract/batch` body {urls[], mode?, clean?, use_llms_txt?, min_runes?, lang?} → bare JSON array.
**Data Shape:** item = {page_content: string, metadata: map[string]string}; maxBatchExtractURLs 20; bounded parallelism MaxConcurrent + aggregate BatchTimeout(len(urls)).

### Decisive source
```go
// batchExtractItem is one entry of the bare-array /extract/batch response.
// The {page_content, metadata} shape is the Open WebUI ExternalWebLoader
// contract - do not wrap it in the Envelope.
type batchExtractItem struct {
	PageContent string            `json:"page_content"`
	Metadata    map[string]string `json:"metadata"`
}
// Target URLs are validated in the fetch path, inside the workers - a bad
// URL becomes an error item instead of failing the whole batch (Open WebUI
// drops every doc on a non-2xx). 400 is reserved for malformed requests.
```

**Flow:** dedupe input URLs → base request from shared knobs (same X-Use-Proxy/X-Proxy-URL/clean/min_runes handling as single extract) → worker per URL with semaphore → per-item error captured into that item only → array returned 200 even when every item errored.
**Invariant:** non-2xx batch responses destroy the entire loader run client-side — per-item errors must ride IN items; malformed requests (no urls array, >20) still deserve 400.
**Probe:** `go test ./core -run TestBatchExtract` (server_extract_test.go pins shape + per-item error isolation).
**Probe executed (real runner):** same command at pin = **11 PASS** — bare-array contract, ≤20 limit, dedupe, invalid mode/empty URLs/bad proxy header rejections, per-URL error isolation, private-network guard per item, timeout derivation, lang body plumbing, disabled-404.
**Python-equivalent probe (executed):**
```bash
grep -n 'ExternalWebloader\|ExternalWebLoader\|page_content' core/server_extract.go | head -4
```

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-openserp", query: "handleBatchExtract batchExtractItem dedupeBatchURLs maxBatchExtractURLs", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt the bare-array {page_content, metadata} contract verbatim if you target Open WebUI-compatible loaders; adapt limits to your gateway; keep per-item error isolation regardless.

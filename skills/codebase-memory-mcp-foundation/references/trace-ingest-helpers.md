<!-- capsule-v2 -->
# Trace ingest helpers — how do you turn OpenTelemetry spans into service-level graph edges?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What pure helpers extract service identity and HTTP info from OTLP payloads for the ingest_traces tool?

## Resource-attribute service name + HTTP-info extraction
**Path/Symbol:** `src/traces/traces.h` (contract 1–40) + tests/test_traces.c:13–43.
**Signature:** OTLP attribute walks: `service.name` from resource attributes; HTTP method/URL/status from span attributes.
**Data Shape:** Input: resource {attributes[]} + spans with attribute key/value pairs (string values). Helpers are PURE (no store access) so the MCP handler owns persistence; missing service name yields NULL, not error.

### Decisive source
```c
/* traces.h — OTLP trace processing helpers.
 * Pure helper functions for extracting data from OpenTelemetry spans.
 * Used by the MCP ingest_traces handler. */
TEST(traces_extract_service_name) { ... }
TEST(traces_extract_service_name_missing) { ... }
TEST(traces_extract_http_info) { ... }
```

**Flow:** decode OTLP JSON → walk resource attributes for `service.name` → per span extract http.method/url/status_code → caller maps spans onto CROSS_HTTP_CALLS-style edges between service nodes.
**Invariant:** Purity keeps wire parsing testable separately from graph writes; absence must be distinguishable (NULL/0-count), never an empty-string service name.
**Probe:** `tests/test_traces.c:traces_extract_service_name`, `traces_extract_service_name_missing` (absence case), `traces_extract_http_info`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_trace_resource_t", limit: 5 });
```

## Verdict
Adopt pure extraction helpers + thin persistent handlers for wire-format ingestion; adapt attribute keys to your OTel conventions; omit the ingest UI if you expose it via MCP only.

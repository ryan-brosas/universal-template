<!-- capsule-v2 -->
# Service pattern classification — how does a resolved callee QN become HTTP_CALLS vs ASYNC vs ROUTE_REG vs CONFIGURES?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** How do you distinguish "gin.GET registers a handler" from "requests.get makes an outbound call" when both end in `.get`?

## Ordered allowlist tables with route-reg priority
**Path/Symbol:** `internal/cbm/service_patterns.c:cbm_service_pattern_match` (~786–830) + table defs (`route_reg_libraries` 318+, http/async/config/grpc/graphql/trpc siblings); enum in `service_patterns.h:14–26`.
**Signature:** `cbm_svc_kind_t cbm_service_pattern_match(const char *resolved_qn);`
**Data Shape:** Each table maps qualified-name substrings → kind. Match order: ROUTE_REG → HTTP → ASYNC → CONFIG → GRPC → GRAPHQL → TRPC. Per-worker TLS cache keyed by the full resolved QN.

### Decisive source
```c
/* Route registration checked first — prevents gin/echo from matching
 * as HTTP clients (both have .get/.post suffixes). */
if ((p = match_qn(resolved_qn, route_reg_libraries))) result = p->kind;
else if ((p = match_qn(resolved_qn, http_libraries)))     result = p->kind;
else if ((p = match_qn(resolved_qn, async_libraries)))    result = p->kind;
...
```
```c
/* Distinguished from HTTP clients: "gin.GET" registers a handler,
 * "requests.get" makes an outbound HTTP call. */
```

**Flow:** pass_calls resolves a callee through the registry → if resolved, classify via this ladder → ROUTE_REG + method-suffix mints a Route node and HANDLES edge; HTTP/ASYNC mint edge to a Route node carrying the canonicalized URL; CONFIG marks config accessors; unmatched stays plain CALLS.
**Invariant:** The ordering IS the semantics — swapping route-reg and http would misclassify every gin router as an HTTP client. Classification runs only AFTER resolution to an in-graph or stdlib-known node.
**Probe:** `tests/test_edge_types_probe.c:handles_gin_go` (route reg) vs `tests/test_lang_contract.c:contract_edge_http_calls` (outbound requests_*), plus `tests/test_infrascan.c:infrascan_http_route_literal_guard_rejects_filesystem_paths` guarding URL literals.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_service_pattern_match", limit: 5 });
```

## Verdict
Adopt the ordered-allowlist-with-priority scheme for classifying library calls; adapt the pattern tables to your ecosystem's libraries; omit the TLS cache if classification is not on your hot path.

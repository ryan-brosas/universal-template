<!-- capsule-v2 -->
# Route canon — how do client call-sites and server handlers written in different frameworks rendezvous on one route identity?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** How do you canonicalize `:id`, `{id}`, `<id>`, `${id}` so cross-language HTTP edges link up?

## Parameter-syntax collapse to "{}"
**Path/Symbol:** `src/pipeline/pass_route_nodes.c:cbm_route_canon_path` (59–129).
**Signature:** `const char *cbm_route_canon_path(const char *in, char *out, size_t out_sz);`
**Data Shape:** Static path text copied verbatim; every parameter token (regardless of framework spelling or captured name) collapses to a single `"{}"`; output never exceeds input length; NULL/too-small buffer returns the pointer untouched (early-out contract).

### Decisive source
```c
/*   :name    Express / React-Router / Rails / typical JS API clients
 *   {name}   Axum / Spring / OpenAPI / ASP.NET
 *   <name>   Flask / Rocket (incl. typed "<int:id>")
 *   ${...}   JS template interpolation captured into the path
 *
 * Parameter names are intentionally discarded so the same logical endpoint
 * matches across services that name the path variable differently. */
bool at_seg_start = (oi == 0) || (out[oi - 1] == '/');
if (c == ':' && at_seg_start && is_route_ident_char(in[i + 1])) { /* consume ident */ }
```

**Flow:** walk input → recognize param openers (`:` only at segment start followed by an ident char, `{`, `<`, `${`) → swallow through the closer or `/` → emit `{}` → copy literal chars → NUL-terminate. Route nodes then key as `__route__<METHOD__><canonpath>` so an Axum handler and a JS fetch client mint the SAME node and DATA_FLOWS/HANDLES/HTTP_CALLS can join.
**Invariant:** Param names are discarded BY DESIGN ("{id}" == ":requestId"); a colon NOT at segment start is literal text.
**Probe:** `tests/test_route_canon.c:route_canon_colon_and_brace_converge` (Axum `{id}` vs JS client `:clientId` produce identical `/clients/{}/authorized-users`), `route_canon_angle_param`, `route_canon_param_name_agnostic`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_route_canon_path", limit: 5 });
```

## Verdict
Adopt the collapse-to-{} grammar and segment-start colon rule for any cross-service route matching; adapt the QN prefix (`__route__METHOD__path`) to your graph schema; omit the SvelteKit filesystem-route phase unless you need convention-based routing.

<!-- capsule-v2 -->
# UI RPC read-only gate — how do you let a browser dashboard drive a code server without handing it mutators?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What request parsing and tool gating make the loopback HTTP UI safe against duplicate headers, traversal, NULs, and destructive tools?

## Strict header parsing + read-only allowlist + 403 on ambiguity
**Path/Symbol:** `tests/test_httpd.c` pins the contract — `httpd_parse_security_headers_and_rejects_duplicates` (221), `ui_server_rpc_allows_only_ui_read_tools` (1086), `ui_server_browse_traversal_probe` (1185), `repo_info_strips_credentials_from_remote` (1825); engine in `src/ui/httpd.c`, server in `src/ui/http_server.c`.
**Signature:** HTTP surface: `POST /rpc` carrying JSON-RPC tools/call; parser `cbm_http_parse_head(raw, len, &req, &body_off, &content_length)`.
**Data Shape:** Duplicate Host/Origin/Content-Type ⇒ 400. Bare-LF terminators rejected. Encoded slashes are not routed; NUL in target rejected. Allowed UI tools = read tier only (list_projects etc.); delete_project/manage_adr/ingest_traces/index_repository ⇒ 403; ambiguous duplicate `"name"` keys ⇒ 403.

### Decisive source
```c
static const char *blocked_tools[] = {"delete_project", "manage_adr",
                                      "ingest_traces", "index_repository"};
... ASSERT_EQ(th_status(resp), 403);
/* Ambiguous duplicate name key must ALSO be refused: */
{"name":"list_projects","name":"delete_project","arguments":{}} → 403
```
```c
char *safe = cbm_ui_git_strip_credentials("https://alice:s3cr3t@github.com/org/repo.git");
ASSERT_STR_EQ(safe, "https://github.com/org/repo.git");  /* path '@' is NOT creds */
```

**Flow:** parse head strictly (case-insensitive names, single-instance security headers) → route with encoded-slash/NUL rejection → same-origin check for browser calls → /rpc maps to the MCP dispatcher under a READ-ONLY allowlist; anything mutating or ambiguous returns 403 before dispatch → repo metadata strips credentials from git remotes before display.
**Invariant:** Parsing rejects rather than normalizes duplicates (an ambiguity attack would otherwise smuggle a second Host/Origin past one layer); the allowlist is positive — new mutators stay blocked by default.
**Probe:** run the named tests above; also `ui_server_oversized_body_rejected`, `ui_server_rejects_non_loopback_host`, `ui_server_slow_request_hits_deadline`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_http_parse_head", limit: 5 });
```

## Verdict
Adopt reject-duplicate-headers + positive read allowlists for any embedded admin UI; adapt origin rules; omit the 3D layout/graph-ui bundle if your frontend is separate.

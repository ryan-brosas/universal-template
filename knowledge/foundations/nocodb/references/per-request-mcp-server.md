<!-- capsule-v2 -->
# Per-request throwaway MCP server — why is a new McpServer+transport built for every HTTP call, and how do tools enforce roles?

**Source:** nocodb (Sustainable Use License) `develop@640fe3b06f`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** How does a stateless HTTP MCP endpoint avoid session state, and where do write tools get gated?

## Stateless transport + role/edition-gated registration
**Path/Symbol:** `packages/nocodb/src/mcp/mcp.service.ts:McpService.handleRequest` (:37–60), `registerTools` (:62–756); route: `mcp/mcp.controller.ts` @All('mcp/:mcpTokenId') with MetaApiLimiterGuard.
**Signature:** `handleRequest(tokenId, context, req, res)`; `registerTools({server, context, user, req})` registers 10 CE tools (getBaseInfo, getTablesList, getTableSchema, queryRecords, getRecord, countRecords, readAttachment, aggregate_single, createRecords, updateRecords, deleteRecords).
**Data Shape:** StreamableHTTPServerTransport with `sessionIdGenerator: undefined`; tool results are `{content:[{type:'text',text:JSON.stringify(...,2)}], isError?}` — every handler catches its own errors into isError:true text.

### Decisive source
```ts
const server = new McpServer({ name: `NoocDB MCP Server`, version: '1.0.0' });
await this.registerTools({ context, user: req.user, server, req });
const transport = new StreamableHTTPServerTransport({
  sessionIdGenerator: undefined,
});
res.on('close', () => {
  transport.close();
  server.close();
});
```
(:43–:57)

**Flow:** controller authenticates via xc-mcp-token header → MCPToken.validateToken(context, token, tokenId) → loads user WITH base/workspace roles and rejects NO_ACCESS BEFORE the service runs → service constructs a FRESH McpServer per request, registers tools against THAT user's permissions (readOnly beacons always; aggregate_single only when !isEE; create/update/deleteRecords only when hasMinimumRole(EDITOR)), connects a sessionless streamable transport, and closes BOTH on res 'close'.
**Invariant:** because registration happens per-request with the request's user in scope, authorization is structural — a viewer literally never receives write-tool definitions rather than receiving them erroring. sessionIdGenerator undefined = pure stateless HTTP mode; no session store to invalidate. Tool annotations carry MCP hints honestly (readOnlyHint on reads; destructiveHint on update/delete). The aggregate gate is EDITION-based (CE-only tool; EE replaces aggregation surface) while writes are ROLE-based.
**Probe:** `cd packages/nocodb && grep -c "registerTool" src/mcp/mcp.service.ts` (=13: 11 registrations + comment refs) and `grep -c "sessionIdGenerator: undefined" src/mcp/mcp.service.ts` (=1) and `grep -c "isEditorPlus" src/mcp/mcp.service.ts` (=2 decl + use) and `grep -c "xc-mcp-token" src/mcp/mcp.controller.ts` (=2 check + cast).
**Direct test:** none upstream for mcp/ — grep probes pin shape; coverage no_recorded_issue @pin.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "McpService handleRequest registerTools StreamableHTTPServerTransport", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt per-request server construction + structural authz via conditional registration + sessionless transport; adapt the tool set to your domain API; omit if you need persistent MCP sessions. Coverage caveat: grep-pinned only.

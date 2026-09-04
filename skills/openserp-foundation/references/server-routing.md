<!-- capsule-v2 -->
# Server routing & middleware — which routes exist and in what middleware order do requests flow?

**Source:** OpenSERP MIT `main@29c7b0fb`; Codebase Memory `ext-aeo-openserp`. **Question:** How are engine routes registered with aliases, and why is the request timeout middleware exempt for /mega/* and /extract*?

## Route table & pipeline
**Path/Symbol:** `core/server.go:NewServerWithOptions` (L141–241), `handleDedicatedEndpoint` (L243–390), `handleParseEndpoint`, `handleMegaEndpoint`, `core/middleware.go` (whole file), graceful shutdown in cmd/serve.go (`listenWithGracefulShutdown`, SetDraining).
**Signature:** registration loops over engines: GET /{endpoint}/search, /{endpoint}/image (+canonical alias when different); POST /{engine}/parse (+alias); GET /mega/{search,image,engines}; GET|POST /extract, POST /extract/batch; /health,/ready,/stats,/stats/{cache,proxy,cb},/openapi.yaml,/docs.
**Data Shape:** fiber app with JSONErrorMiddleware as ErrorHandler; BodyLimit 10MB.

### Decisive source
```go
app.Use(fiberrecover.New(...))       // defense-in-depth: handlers bypassing invokeEngine
app.Use(RequestContextMiddleware())  // X-Request-ID echo-or-generate(uuid v7), X-Tenant, query hash → ctx
if opts.RequestTimeout > 0 { app.Use(RequestTimeoutMiddleware(opts.RequestTimeout)) }
if opts.EnableCORS { app.Use(CORSMiddleware(opts.CORS)) }   // exposes X-Cache/X-Proxy-* etc
app.Use(RequestLoggerMiddleware())
// RequestTimeoutMiddleware:
if strings.HasPrefix(c.Path(), "/mega/") || c.Path() == "/extract" || c.Path() == "/extract/batch" {
	return c.Next()   // those manage their own budgets (MegaTimeout, BatchTimeout)
}
ctx,_ := context.WithTimeout(c.UserContext(), timeout)
```
Dedicated endpoint flow: X-Use-Profile validation → InitFromContext → validateRequestProxyURL → resolveFormat → cache probe (JSON, no extract, no bypass-market) → SearchPrimary|WithFallback → applyProxyHeaders → envelope build → optional extraction enrichment → cacheEnvelopeIfEligible → X-Fallback-Engine header when usedEngine≠primary. fasthttp never cancels on client disconnect — the deadline must be attached to the user context manually.
**Invariant:** health "unhealthy"/"degraded" stays HTTP 200 except all-engines-unhealthy ⇒ 503 (orchestrators shouldn't restart transient blocks); /ready flips to "draining"+503 BEFORE ShutdownWithTimeout so LBs stop routing during drain.
**Probe:** `go test ./core -run 'TestServer|TestMiddleware'` — server_test.go pins alias routes, header echoes, fallback/cache interplay, health semantics; middleware_test.go pins exemption paths.
**Probe executed (real runner):** same command at pin = **2 PASS** as written; the full routing plane executed via `go test ./core -run 'TestDedicatedEndpoint|TestDuckDuckGoDedicatedAliasRoutes|TestHealthEndpoint|TestReadinessEndpoint|TestOpenAPISpecEndpoint|TestDocsEndpoint'` = **15 PASS** (alias routing, request-ID echo, CORS, fallback/cache interplay, health/readiness semantics).
**Python-equivalent probe (executed):**
```bash
grep -n 'engineEndpointName\|resolveEngineAlias' core/server.go | head -4   # duck↔duckduckgo dual registration
grep -c 'app.Get\|app.Post' core/server.go                                  # route count
```

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-openserp", query: "NewServerWithOptions handleDedicatedEndpoint RequestContextMiddleware RequestTimeoutMiddleware SetDraining", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt the middleware order (recover→request-context→timeout(exempt self-budgeting paths)→CORS→logger) and draining readiness; adapt framework primitives; omit OpenAPI/docs embedding if you document elsewhere.

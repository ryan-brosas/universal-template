<!-- capsule-v2 -->
# Model reference routing — how does one model string route to local, remote, or cloud execution?

**Source:** Ollama MIT `main@fb30760996871fa9460115c753afd2c60d4ab0f7`; Codebase Memory `ext-ollama`. **Question:** How is `model:tag:cloud` parsed, validated, and proxied without leaking cloud errors into the local API surface?

## parseAndValidateModelRef + proxy ladder
**Path/Symbol:** `server/model_resolver.go:14-55` (`parsedModelRef`, `parseAndValidateModelRef`), `server/routes.go` GenerateHandler :265-273 / ChatHandler :2477-2490 (`proxyCloudJSONRequest`), remote-model branch :302-394 (Chat :2566-2660). **Signature:** `func parseAndValidateModelRef(raw string) (parsedModelRef, error)`.
**Data Shape:** `parsedModelRef{Original, Base, Name model.Name, Source}` — Source ∈ {Unspecified, Local, Cloud} from an explicit `:cloud` suffix; Base strips it; Name applies registry defaults (`registry.ollama.ai/library/...`). Cloud-disabled policy via `internalcloud.Status()` (OLLAMA_NO_CLOUD).

### Decisive source
```go
if modelRef.Source == modelSourceCloud {
    req.Model = modelRef.Base
    proxyCloudJSONRequest(c, req, cloudErrRemoteInferenceUnavailable)
    return
}
...
// manifest-declared REMOTE models (RemoteHost+RemoteModel) proxy as streaming NDJSON:
for k, v := range m.Options { if _, ok := req.Options[k]; !ok { req.Options[k] = v } } // defaults merge
client := api.NewClient(remoteURL, http.DefaultClient)
err = client.Chat(c, &req, fn)   // fn rewrites Model back to origModel per chunk
```

**Flow:** Every handler starts here. Explicit `:cloud` ⇒ strip suffix and forward to the cloud proxy with a stable unavailable-error constant. Otherwise resolve locally; a manifest with RemoteHost/RemoteModel acts as a self-hosted reverse-proxy entry: hostname must appear in `envconfig.Remotes()` allowlist or 400; model/system/options defaults merge under request precedence; each streamed chunk gets `Model/RemoteModel/RemoteHost` rewritten so clients see the name they asked for; AuthorizationErrors surface a `signin_url`. Local-only guard: `Source==Local` + remote manifest fields ⇒ 404 (an explicit local request must never silently round-trip).
**Invariant:** The user-visible model name is preserved end-to-end; option merging is first-writer-wins (request beats manifest); allowlist check happens before ANY outbound call.
**Probe:** `grep -cF "modelSourceCloud" server/model_resolver.go` → `2`; `grep -cF "proxyCloudJSONRequest(c, req" server/routes.go` → `5` handlers. Direct tests: `server/routes_cloud_test.go` (1,299L, PASS at pin).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ollama", query: "parseAndValidateModelRef cloud source", limit: 5 });
```

## Verdict
Adopt suffix-parsed source enum + defaults-merge + identity-rewriting proxy. Adapt the cloud error constants and allowlist source to your deployment; omit the remote-manifest branch if you have no federation.

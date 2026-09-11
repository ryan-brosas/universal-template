<!-- capsule-v2 -->
# Chat dual execution modes — when does /api/chat render the prompt in Go vs delegate templating to llama-server?

**Source:** Ollama MIT `main@fb30760996871fa9460115c753afd2c60d4ab0f7`; Codebase Memory `ext-ollama`. **Question:** What decides native (server-side Jinja) chat vs Ollama-rendered chat, and what must flip together?

## chatModeForModel + llamaServerConfigForModel coupling
**Path/Symbol:** `server/routes.go:2350-2374` (`chatExecutionMode`, `chatModeForModel`, `llamaServerConfigForModel`, `usesOllamaRenderedChat`, `shouldUseGoTemplate`), dispatch at :2673-2676 (`handleNativeChat`). **Signature:** `func chatModeForModel(m *Model) chatExecutionMode`.
**Data Shape:** `chatExecutionModeNative` = llama-server applies the model's embedded Jinja chat template. `chatExecutionModeRendered` = Ollama renders the full prompt string in Go (renderer registry, harmony prefill, or legacy Go template) and sends plain completion.

### Decisive source
```go
func usesOllamaRenderedChat(m *Model) bool {
    return m != nil && (m.Config.Renderer != "" || m.Config.Parser != "" ||
        shouldUseHarmony(m) || shouldUseGoTemplate(m))
}
func llamaServerConfigForModel(m *Model) llm.LlamaServerConfig {
    return llm.LlamaServerConfig{
        DisableJinja:   usesOllamaRenderedChat(m),  // MUST match the mode
        DraftModelPath: m.DraftPath,
    }
}
```

**Flow:** Mode is computed per request from model config: an explicit `Renderer` OR explicit `Parser` in the manifest, a harmony (gpt-oss family) template, or an eligible Go template ⇒ Rendered; otherwise Native. The SAME predicate also sets `DisableJinja` on the server launch config — so the runner's template behavior is decided once at LOAD time and every chat on that runner must agree. ChatHandler then branches: native path marshals messages+tools to `r.Chat(...)` after truncation; rendered path runs `parsers.ParserForName(m.Config.Parser)` + `chatPrompt(...)` into `r.Completion(...)`. `DebugRenderOnly` returns the exact rendered prompt without inference — the porting debugger for this whole plane.
**Invariant:** `DisableJinja` and the runtime branch must be derived from one predicate; flipping mode per-request while the server was loaded with the other setting double-applies (or drops) the chat template. Capability detection (`shouldUseGoTemplate` honors `OLLAMA_GO_TEMPLATE` env precedence) feeds the same predicate.
**Probe:** `grep -cF "DisableJinja:   usesOllamaRenderedChat(m)" server/routes.go` → `1`; `grep -c "chatExecutionModeNative" server/routes.go` → `5` sites. Direct test: `go test ./server/ -run TestChat` suite incl. `routes_generate_test.go` (PASS at pin).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ollama", query: "chatModeForModel native rendered", limit: 5 });
```

## Verdict
Adopt single-predicate mode selection with the launch-config flag derived from it. Adapt the predicate's inputs to your renderer/parser inventory; omit harmony/Go-template arms if you only port renderer-driven models.

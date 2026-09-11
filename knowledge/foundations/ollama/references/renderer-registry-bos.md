<!-- capsule-v2 -->
# Renderer registry + BOS — how are per-family prompt renderers selected and what does the completion loop need from them?

**Source:** Ollama MIT `main@fb30760996871fa9460115c753afd2c60d4ab0f7`; Codebase Memory `ext-ollama`. **Question:** How do you plug ~25 model-specific prompt renderers (qwen3.5/3.8, glm4.7, gemma4, olmo3 variants…) behind one call site?

## Renderer interface + name resolution
**Path/Symbol:** `model/renderers/renderer.go:11-125` (`Renderer` interface :11-14, registries :16-36, `RenderWithRenderer` :43-51, `LeadingBOSForRenderer` :53-61, `rendererForName` switch :63-124). **Signature:** `type Renderer interface { Render(messages []api.Message, tools []api.Tool, think *api.ThinkValue) (string, error); LeadingBOS() string }`.
**Data Shape:** Global `RenderImgTags bool` set by the server package on init — the ONLY environmental input; keeps renderer constructors pure for tests. Variants encode family quirks as struct fields (`Qwen35Renderer{isThinking:true, emitEmptyThinkOnNoThink:true}`, `Olmo3Renderer{UseExtendedSystemMessage}`, `Gemma4Renderer{emptyBlockOnNothink}`).

### Decisive source
```go
func LeadingBOSForRenderer(name string) string {
    renderer := rendererForName(name)
    if renderer == nil { return "" }
    return renderer.LeadingBOS()
}
// ChatHandler completion request wiring:
LeadingBOS: leadingBOSForModel(m),        // routes through the registry
ToolCallTag: toolCallTagForCompletion(toolParser),
PreservedTokens: preservedTokensForCompletion(builtinParser),
```

**Flow:** Manifest `renderer=` name → registry hit or legacy switch → Rendered-mode chat calls `RenderWithRenderer(resolveRendererName(m), msgs, processedTools, req.Think)` inside `renderPrompt`. The same name ALSO supplies `LeadingBOS()` which travels in the CompletionRequest so llama-server prepends the family's required begin-of-sentence token exactly once; a nil renderer yields empty BOS rather than error (models without one are normal). Think requests pass level (`low|medium|high`) through `ThinkValue`, letting each family map effort to its native controls. Unknown renderer names error at render time with `unknown renderer %q`.
**Invariant:** Renderer selection and BOS must come from ONE resolver so they can't disagree; renderers receive already-renamed tools (harmony's Init output) and must not re-derive tool schemas.
**Probe:** `grep -cF "func LeadingBOSForRenderer" model/renderers/renderer.go` → `1`; `grep -cF "chatExecutionModeNative" server/routes.go` → `5`. Direct tests: `go test ./model/renderers/` incl. reference-template golden tests (PASS at pin).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ollama", query: "RenderWithRenderer LeadingBOS renderer", limit: 6 });
```

## Verdict
Adopt constructor-registry + variant-struct-field pattern and the single-resolver BOS coupling. Adapt the interface to your message/tool types; omit image-tag mode when your models are text-only.

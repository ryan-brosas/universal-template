<!-- capsule-v2 -->
# Model capability ladder — where do completion/tools/vision/thinking capabilities actually come from?

**Source:** Ollama MIT `main@fb30760996871fa9460115c753afd2c60d4ab0f7`; Codebase Memory `ext-ollama`. **Question:** How is a capability like "tools" derived from GGUF metadata, templates, parsers, projectors, and family lists without hardcoding per-model tables?

## Capabilities() aggregation pipeline
**Path/Symbol:** `server/images.go:103-138` (`Capabilities`, `capabilitiesForTemplate`), :140-186 (`configCapabilities`+`ggufCapabilities` incl. template-string sniffing `chatTemplateHasToolSupport/HasToolRoundTrip/HasThinkingSupport` :202-234), :236-292 (Go-template AST caps + `shouldPreferChatTemplate`), :393-483 (`projectorCapabilities`, `templateCapabilities`, `parserCapabilities`, `modelFamilyCapabilities`, `filterUnsupportedCapabilities` with vision/audio suppressors). **Signature:** `func (m *Model) Capabilities() []model.Capability`.
**Data Shape:** Sources feed one accumulated list in FIXED order: config → gguf (arch, projector presence, chat-template keyword scan) → selected template source → parser interface → model family (`gptoss` ⇒ thinking) → suppression filters. Template-source enum: Selected / Go / Chat.

### Decisive source
```go
func shouldPreferChatTemplate(chatTemplate string, chatTemplateCaps []model.Capability,
    goTemplate *template.Template, goTemplateCaps []model.Capability) bool {
    if hasMoreCapabilities(chatTemplateCaps, goTemplateCaps) {
        return !goTemplateHasToolRoundTrip(goTemplate) || chatTemplateHasToolRoundTrip(chatTemplate)
    }
    if !sameCapabilities(chatTemplateCaps, goTemplateCaps) ||
        !slices.Contains(chatTemplateCaps, model.CapabilityTools) ||
        !slices.Contains(goTemplateCaps, model.CapabilityTools) { return false }
    return chatTemplateHasToolRoundTrip(chatTemplate) && !goTemplateHasToolRoundTrip(goTemplate)
}
// parserCapabilities derives from the INTERFACE, not a table:
if builtinParser.HasToolSupport()     { capabilities = appendCapability(capabilities, model.CapabilityTools) }
if builtinParser.HasThinkingSupport() { capabilities = appendCapability(capabilities, model.CapabilityThinking) }
```

**Flow:** A model "supports tools" if ANY layer proves it: gguf chat template contains tool-call syntax, the Go template renders tool round-trips, its builtin parser advertises HasToolSupport, or config lists it. When both a Go template and an embedded Jinja template exist, `shouldPreferChatTemplate` picks by capability-count then tool-round-trip fidelity — this decides `PreferChatTemplate` and hence the whole rendered-vs-native path. Suppression runs LAST (e.g. audio-capable projector on a text-only arch loses CapabilityAudio). Results are cached per model instance (`capabilitiesCached`) — set inside the inference cache flight so the expensive GGUF reads happen once.
**Invariant:** appendCapability dedupes; the order matters because suppression must see the final union; template preference must consider round-trip support or tools break silently under the "better" template.
**Probe:** `grep -cF "goTemplateHasToolRoundTrip(goTemplate)" server/images.go` → `2`; `grep -cF "shouldUseGoTemplate(m)" server/images.go` → `2`. Direct test: `server/images_test.go` capability cases (`go test ./server/` PASS at pin).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ollama", query: "capabilities template goTemplate chatTemplate prefer", limit: 5 });
```

## Verdict
Adopt layered derivation ending in suppression filters, and derive parser caps from interfaces. Adapt the keyword-sniffing heuristics to your template dialects; omit projector/audio layers for text-only servers.

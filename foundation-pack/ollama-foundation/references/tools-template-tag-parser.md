<!-- capsule-v2 -->
# Template-derived tool-call tag parser — how are tool calls extracted when the model's format is defined by its chat template?

**Source:** Ollama MIT `main@fb30760996871fa9460115c753afd2c60d4ab0f7`; Codebase Memory `ext-ollama`. **Question:** How do you discover the tool-call delimiter from an arbitrary Go chat template and parse streamed JSON arguments safely across chunk boundaries?

## tools.Parser (tag inference → buffered JSON scanning)
**Path/Symbol:** `tools/template.go:17-46` (`parseTag`, `findToolCallNode`), `tools/tools.go` (`NewParserWithTag` :45-51, `Add` :54-105, `findTag` :110-124, `parseToolCall` :128-160, `findTool` :162-217, `findArguments` :219-345, `done` :347-388, `Content` :394-404). **Signature:** `func NewParser(tmpl *template.Template, tools []api.Tool) *Parser`; `func (p *Parser) Add(s string) (calls []api.ToolCall, content string)`.
**Data Shape:** States LookingForTag/ToolCalling/Done; buffer holds unemitted bytes; `n` counts emitted calls. Tag default `"{"` when the template yields nothing.

### Decisive source
```go
// parseTag: find the {{if .ToolCalls}} branch, take its first text node,
// cut at the first '{', trim — the literal prefix IS the tool-call tag.
tag, _, _ = strings.Cut(tag, "{")
tag = strings.TrimSpace(tag)
if tag == "" { tag = "{" }   // bare JSON mode
// Add(): brace tags only parse if FIRST non-whitespace char is { or [:
if p.tag == "{" || p.tag == "[" {
    if strings.TrimSpace(content) != "" { p.state = toolsState_Done; return nil, content + string(p.buffer) }
}
// findTool(): never match a PREFIX of a longer tool name at buffer end
for i := 1; i <= min(len(buf), len(longest)); i++ {
    tail := buf[len(buf)-i:]
    for _, t := range tools {
        if len(tail) < len(t.Function.Name) && bytes.HasPrefix([]byte(t.Function.Name), tail) {
            return nil, 0    // could still become "get_weather" — wait for more bytes
        }
    }
}
```

**Flow:** ChatHandler constructs this parser only for models WITHOUT a builtin parser but WITH tools requested (`tools.NewParser(m.Template.Template, req.Tools)`). Streaming: pre-tag text streams straight through; once the tag appears, name matching scans candidates left-to-right preferring earliest-then-longest, argument extraction is a hand-rolled brace-depth scanner honoring string escapes (`inString`/`escaped` flags) that returns the first balanced `{...}` after the tool name; multiple calls loop until `parseToolCall` misses. For brace tags `done()` counts balance to decide completion and `Content()` returns the raw buffer when zero calls were parsed (plain JSON output must not be swallowed). Every parsed call gets `Index: p.n++` so OpenAI-compat streaming can chunk it.
**Invariant:** Partial tool-name suffixes must hold emission (the "get"/"get_weather" rule); brace-mode must bail to Done on any leading non-whitespace non-brace content or prose gets eaten; argument scanning must track escape state or `{"a":"}"}` desyncs.
**Probe:** `grep -cF "return \"{\"" tools/template.go` → `4` fallback sites; `grep -cF "bytes.HasPrefix(name, tail)" tools/tools.go` → `1`. Direct tests: `go test ./tools/` PASS at pin.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ollama", query: "tools Parser Add findTag parseToolCall", limit: 5 });
```

## Verdict
Adopt template-AST tag inference plus the escape-aware scanner. Adapt `parseTag` if your templates aren't Go `text/template`; omit brace-tag heuristics if your models always use explicit delimiters.

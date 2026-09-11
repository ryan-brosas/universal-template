<!-- capsule-v2 -->
# Builtin parser registry + preserved tokens — how are per-model stream grammars plugged into the completion loop?

**Source:** Ollama MIT `main@fb30760996871fa9460115c753afd2c60d4ab0f7`; Codebase Memory `ext-ollama`. **Question:** How do ~20 model-specific output formats (qwen3, glm, gemma4, deepseek3, …) integrate without the server knowing any of their internals?

## parsers.Parser interface + registry
**Path/Symbol:** `model/parsers/parsers.go:13-107` (`Parser` interface :13-31, `ParserRegistry`/global registry :33-49, `ParserForName` switch :51-105, `PassthroughParser` :107+). **Signature:** `type Parser interface { Init(tools []api.Tool, lastMessage *api.Message, thinkValue *api.ThinkValue) []api.Tool; Add(s string, done bool) (content, thinking string, calls []api.ToolCall, err error); PreservedTokens() []string; HasToolSupport() bool; HasThinkingSupport() bool }`.
**Data Shape:** Registry maps config names (`m.Config.Parser`) to constructors; switch fallback covers legacy names incl. aliases (`ornith`→Qwen35Parser, `poolside-v1`→LagunaV8Parser). Unknown name ⇒ nil ⇒ ChatHandler falls back to generic thinking+tools parsers.

### Decisive source
```go
// Add processes streamed content and returns parsed content, thinking, and tool calls
// The done flag indicates if this is the last chunk (used for draining accumulators)
Add(s string, done bool) (content string, thinking string, calls []api.ToolCall, err error)
// PreservedTokens returns parser grammar tokens that must remain visible in
// llama-server detokenized output for this parser to recognize boundaries.
PreservedTokens() []string
```
```go
// ChatHandler wiring:
processedTools = builtinParser.Init(req.Tools, lastMessage, req.Think)  // harmony renames tools here
...
PreservedTokens: preservedTokensForCompletion(builtinParser),           // forwarded to runner
...
content, thinking, toolCalls, err := builtinParser.Add(r.Content, r.Done)
if err != nil { parserErr = err; cancel(); return }                     // mid-stream parse error aborts cleanly
```

**Flow:** Model declares `parser=` in its manifest; ChatHandler instantiates via `ParserForName`, calls `Init` once (gets back possibly-RENAMED tools), feeds every runner chunk through `Add`, assigns fresh tool-call IDs itself (`toolCallId()`), and on parse ERROR cancels the upstream request and emits one `{"error": ...}` frame instead of wedging the stream (commit e0c95a5 regression: a mid-stream parser error used to hang chat/generate). `PreservedTokens` tells llama-server which grammar tokens must survive detokenization so boundary detection works; capabilities advertised by `HasToolSupport/HasThinkingSupport` feed BOTH the capability ladder (`server/images.go parserCapabilities`) and structured-outputs gating.
**Invariant:** Parsers never write to the client — they return values and let ChatHandler emit; `done=true` must flush any accumulator exactly once; a nil parser is a legal "no builtin" answer, not an error.
**Probe:** `grep -cF "PreservedTokens() []string" model/parsers/parsers.go` → `2` (interface + passthrough); `grep -nF "PreservedTokens" server/routes.go` → `:668` (request field) and `:2316` (helper). Direct tests: `go test ./model/parsers/` PASS at pin; integration pin `server/routes_parse_error_test.go`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ollama", query: "ParserForName registry passthrough preserved", limit: 5 });
```

## Verdict
Adopt the five-method Parser contract with done-flag draining and error-cancel semantics. Adapt the registry to your model inventory; the interface shape is the whole port.

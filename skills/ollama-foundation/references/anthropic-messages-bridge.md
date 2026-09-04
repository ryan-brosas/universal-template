<!-- capsule-v2 -->
# Anthropic Messages bridge — what does a faithful /v1/messages shim translate, and where does it deliberately bend?

**Source:** Ollama MIT `main@fb30760996871fa9460115c753afd2c60d4ab0f7`; Codebase Memory `ext-ollama`. **Question:** How do you map Anthropic requests (system blocks, thinking config, effort levels, max_tokens) onto an Ollama-shaped chat backend and stream back Anthropic SSE events?

## FromMessagesRequest + AnthropicMessagesMiddleware + StreamConverter
**Path/Symbol:** `anthropic/anthropic.go:297-407` (`FromMessagesRequest`), :718-730 (`StreamConverter` struct), :749-980 (`Process`), `middleware/anthropic.go:731-810` (`AnthropicMessagesMiddleware`, `relax_thinking`, writer stack). **Signature:** `func FromMessagesRequest(r MessagesRequest) (*api.ChatRequest, error)`; middleware re-encodes the converted request into `c.Request.Body` and swaps `c.Writer`.
**Data Shape:** System accepts string OR content-block array (text blocks concatenated). Options map: `max_tokens→num_predict` (required >0), temperature/top_p/top_k/stop passthrough. Thinking precedence: explicit `thinking.type enabled/disabled` wins; else `output_config.effort ∈ {low,medium,high,max}` becomes a ThinkValue effort string with `xhigh→high` normalization.

### Decisive source
```go
// claude-code-style clients send think=true to non-thinking models; the server
// must not hard-fail them:
c.Set("relax_thinking", true)
...
// ChatHandler counterpart:
if _, ok := c.Get("relax_thinking"); ok {
    slog.Warn("model does not support thinking, relaxing thinking to nil", "model", req.Model)
    req.Think = nil
} else {
    c.JSON(http.StatusBadRequest, gin.H{"error": fmt.Sprintf("%q does not support thinking", req.Model)})
}
// Built-in web_search collision rule:
if hasBuiltinWebSearch && !strings.HasPrefix(t.Type, "web_search") && t.Name == "web_search" { continue } // drop user tool
```

**Flow:** Middleware validates required fields (model, positive max_tokens, ≥1 message) with Anthropic-style error envelopes → converts to internal ChatRequest → JSON-re-encodes it as the body so the EXISTING `/api/chat` handler runs unmodified → installs `AnthropicWriter` whose `writeResponse` feeds each internal NDJSON line to `StreamConverter.Process` producing ordered events (`message_start`, per-block `content_block_start/delta/stop`, `message_delta` usage, `message_stop`) written as `event:`+`data:` SSE. Streaming headers set only when requested; input tokens are ESTIMATED up-front (`EstimateInputTokens`) because real counts arrive only at completion. A `web_search`-typed tool upgrades the writer to `WebSearchAnthropicWriter` which intercepts the model's web_search function call, executes it server-side (5-minute loop context), and splices `server_tool_use`/`web_search_tool_result` blocks before the final text — usage deltas across loop iterations are rebased so clients see one logical turn.
**Invariant:** Conversion must be total (any unconvertible block = 400 before the handler runs); relax_thinking must be set for EVERY /v1/messages request or claude-code integrations break on non-thinking models; the built-in-vs-user web_search name collision always resolves toward the built-in.
**Probe:** `grep -cF 'c.Set("relax_thinking", true)' middleware/anthropic.go` → `1`; `grep -cF "NewStreamConverter(messageID, req.Model, estimatedTokens)" middleware/anthropic.go` → `1`. Direct tests: `go test ./middleware/` (2,959-line anthropic_test.go) PASS at pin.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ollama", query: "StreamConverter anthropic events process", limit: 5 });
```

## Verdict
Adopt convert→re-encode-body→reuse-native-handler→writer-swap architecture plus relax_thinking and effort normalization. Adapt event vocabulary versions to your API target; omit WebSearchAnthropicWriter if you have no server-side search executor.

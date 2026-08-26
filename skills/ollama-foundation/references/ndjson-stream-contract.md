<!-- capsule-v2 -->
# NDJSON stream + error frames — what is Ollama's native wire contract that every compat layer consumes?

**Source:** Ollama MIT `main@fb30760996871fa9460115c753afd2c60d4ab0f7`; Codebase Memory `ext-ollama`. **Question:** How are streaming responses, mid-stream errors, and status codes encoded on /api/chat and /api/generate?

## streamResponse + writeChatResponse channel protocol
**Path/Symbol:** `server/routes.go:2097-2144` (`streamResponse`), :2376-2438 (`writeChatResponse` non-stream aggregation), :2070-2095 (`waitForStream` for pull/push progress). **Signature:** `func streamResponse(c *gin.Context, ch chan any)` — `ch` carries `api.ChatResponse`/`api.GenerateResponse` OR `gin.H{"error": string, "status": int}`.
**Data Shape:** Success frames: one JSON object per line + `\n`, Content-Type `application/x-ndjson`. Error BEFORE any byte: real HTTP status via `c.JSON(status, ...)`. Error AFTER streaming began: 200 continues but the error frame is the terminal line (HTTP headers are already committed).

### Decisive source
```go
if h, ok := val.(gin.H); ok {
    if e, ok := h["error"].(string); ok {
        status, ok := h["status"].(int)
        if !ok { status = http.StatusInternalServerError }
        if !c.Writer.Written() {
            c.Header("Content-Type", "application/json")
            c.JSON(status, gin.H{"error": e})       // pre-stream: proper status code
        } else {
            json.NewEncoder(c.Writer).Encode(gin.H{"error": e}) // mid-stream: terminal frame
        }
        return false
    }
}
// Non-stream aggregation (writeChatResponse): concat thinking+content across
// chunks into builders, collect ALL toolCalls and logprobs, keep LAST Done frame.
```

**Flow:** Handlers own a goroutine that closes `ch` on completion; the writer loop distinguishes payload vs error by TYPE (not sentinel values). Non-stream mode drains the whole channel: strings.Builder accumulation for thinking/content, tool-call slice append, logprob concatenation — then emits exactly one response whose metrics come from the final Done frame. The same channel protocol feeds the OpenAI/Anthropic writers: they unmarshal each line independently, so an error frame becomes `writeError` with the embedded status.
**Invariant:** A handler must ALWAYS close its channel (defer close) or clients hang; error frames must carry machine-readable status; once bytes are written you cannot change the status code — hence the two-phase error policy. Unload requests (empty prompt/messages + keep_alive=0) short-circuit to a synthetic `DoneReason:"unload"` frame WITHOUT touching the scheduler queue beyond expireRunner.
**Probe:** `grep -cF "if !c.Writer.Written()" server/routes.go` → `1` in streamResponse; direct tests: `server/routes_test.go` + `routes_generate_test.go` streaming cases (PASS at pin).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ollama", query: "streamResponse waitForStream ndjson", limit: 5 });
```

## Verdict
Adopt typed-channel streaming with the written-vs-not error split. Adapt frame schemas to your API; this contract is the seam every external codec plugs into, so port it first.

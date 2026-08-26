<!-- capsule-v2 -->
# OpenAI chat streaming codec — how does an NDJSON internal stream become spec-exact SSE chunks?

**Source:** Ollama MIT `main@fb30760996871fa9460115c753afd2c60d4ab0f7`; Codebase Memory `ext-ollama`. **Question:** What are the exact rules for chunk splitting, timestamps, finish_reason, and the usage trailer when bridging Ollama's internal stream to `/v1/chat/completions`?

## ChatWriter + ToStreamChunks + FinishChunk
**Path/Symbol:** `middleware/openai.go:30-40` (`ChatWriter` state), :80-172 (`writeResponse`), `openai/openai.go:344-367` (`ToStreamChunks` mixed-response split), :369-395 (`FinishChunk`). **Signature:** `func (w *ChatWriter) writeResponse(data []byte) (int, error)` — data is one marshaled `api.ChatResponse` NDJSON line.
**Data Shape:** Writer flags `stream/streamOptions/id/toolCallSent/firstChunkSent/createdAt`. Internal protocol: every line is a full ChatResponse; `Done:true` with empty message = metrics trailer; errors arrive as JSON objects with non-200 status handled by `writeError`.

### Decisive source
```go
// One logical emission with BOTH thinking and content becomes TWO chunks:
hasMixedResponse := r.Message.Thinking != "" && (r.Message.Content != "" || len(r.Message.ToolCalls) > 0)
reasoningChunk.Choices[0].Delta.Content = nil          // split 1: reasoning only
contentOrToolCallsChunk.Choices[0].Delta.Reasoning = "" // split 2: content/tools, same timestamp
// Timestamps pinned once per stream:
if w.createdAt.IsZero() { w.createdAt = chatResponse.CreatedAt }
chatResponse.CreatedAt = w.createdAt
// Metrics-only trailer suppressed (OpenAI jumps straight to finish):
isEmptyTrailer := chatResponse.Done && w.firstChunkSent && content=="" && thinking=="" && noToolCalls && noLogprobs
...
reason := cmp.Or(r.DoneReason, "stop")
if reason == "stop" && toolCallSent { reason = "tool_calls" } // ONLY overrides stop
```

**Flow:** Per line: pin shared `createdAt`; skip empty trailers unless nothing was ever sent (wholly empty completions still open with a role chunk); emit 1-2 delta chunks (`includeRole` only on the first); on Done emit a dedicated EMPTY-delta finish chunk carrying finish_reason (spec: finish rides its own chunk), then — if `stream_options.include_usage` — a SECOND marshal of the same finish object mutated to `Choices:[]` + Usage, then literal `data: [DONE]`. `toolCallSent` latches on first tool delta so an unterminated stream still finishes as `tool_calls`, but unknown DoneReasons pass through untouched.
**Invariant:** Never emit two role chunks; never let the metrics trailer surface as an empty content chunk; usage must be a separate chunk with empty choices after the finish chunk; all chunks in one stream share one `created`.
**Probe:** `grep -cF "isEmptyTrailer" middleware/openai.go` → `2` (def + use); `grep -cF 'w.createdAt = chatResponse.CreatedAt' middleware/openai.go` → `1`; `grep -cF 'SystemFingerprint: "fp_ollama"' openai/openai.go` → `5` response shapes. Direct tests: `middleware/openai_test.go` + `openai/openai_test.go` (`go test ./middleware/ ./openai/` PASS at pin).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ollama", query: "ChatWriter streamOptions includeRole finish", limit: 6 });
```

## Verdict
Adopt the codec byte-for-byte: mixed-split, pinned created, trailer suppression, finish+usage+DONE triple. Adapt field names to your API types; omit the completion/completions writer twins if you only bridge chat.

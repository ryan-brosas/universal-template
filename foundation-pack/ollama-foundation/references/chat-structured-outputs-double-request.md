<!-- capsule-v2 -->
# Structured-outputs double request — how does JSON-schema constraint apply without corrupting thinking/tool output?

**Source:** Ollama MIT `main@fb30760996871fa9460115c753afd2c60d4ab0f7`; Codebase Memory `ext-ollama`. **Question:** How can a grammar-constrained generation be combined with a thinking model that must first emit free-form reasoning?

## ChatHandler structuredOutputsState machine
**Path/Symbol:** `server/routes.go:2913-3010` (state consts :2905-2909, force-format suppression :2918-2924, ReadyToApply trigger in builtin-parser arm :2856-2864 and thinking arm :2877-2890, cancellation swallow :2977-2985, replay loop :2987-3008). **Signature:** closure over `structuredOutputsState int` {None, ReadyToApply, Applying} inside the streaming goroutine.
**Data Shape:** First pass runs with `currentFormat = nil` (grammar OFF) while state==None and the model is thinking-capable; collected thinking is buffered in `tb strings.Builder`.

### Decisive source
```go
// inside builtin parser arm — first CONTENT token flips the plan:
if structuredOutputsState == structuredOutputsState_None && req.Format != nil &&
    tb.String() != "" && res.Message.Content != "" {
    structuredOutputsState = structuredOutputsState_ReadyToApply
    cancel()          // abort the unconstrained completion
    return
}
...
if structuredOutputsState == structuredOutputsState_ReadyToApply &&
    strings.Contains(err.Error(), "context canceled") && c.Request.Context().Err() == nil {
    // ONLY ignore the self-inflicted cancel; real client cancels still error out
} else {
    s.sched.expireRunnersForRuntimeOOM(m, err); ch <- gin.H{"error": ...}; return
}
// replay: append assistant message holding ONLY the thinking, re-render, re-run WITH format
msgs = append(msgs, api.Message{Role: "assistant", Thinking: tb.String()})
prompt, _, err = chatPrompt(...)
if shouldUseHarmony(m) || (builtinParser != nil && m.Config.Parser == "harmony") {
    prompt += "<|end|><|start|>assistant<|channel|>final<|message|>" // pin final channel
}
continue // outer for{} → second Completion with req.Format applied
```

**Flow:** Thinking streams normally (grammar off — a constrained decode would break tag discipline). The instant parsed non-thinking content appears, cancel the run; swallow exactly the "context canceled" error when the CLIENT context is still alive; append `{role: assistant, thinking: <collected>}` to history; re-render the prompt and loop — now `currentFormat = req.Format` because state left None. Harmony needs the explicit `<|end|><|start|>assistant<|channel|>final<|message|>` suffix because its renderer cannot disambiguate continue-thinking vs start-final from an all-thinking last message. `forceImmediate` bypasses the two-pass entirely when think=false is requested with a thinking-capable builtin parser.
**Invariant:** The swallowed error must be guarded by BOTH "canceled" text AND live client context — otherwise genuine disconnects masquerade as replays; the replayed prompt carries the thinking as assistant history so the model never regenerates it under grammar.
**Probe:** `grep -cF "structuredOutputsState_ReadyToApply" server/routes.go` → `5`; `grep -cF 'prompt += "<|end|><|start|>assistant<|channel|>final<|message|>"' server/routes.go` → `1`. Direct tests: `server/routes_generate_test.go` structured-output cases (`go test ./server/ -run TestChat` PASS at pin).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ollama", query: "ChatHandler structured outputs thinking", limit: 5 });
```

## Verdict
Adopt two-pass generate→cancel→replay-with-grammar using thinking-as-history, plus the narrow self-cancel swallow. Adapt the harmony channel-pin literal to your renderer's stop sequence; omit forceImmediate if you have no think-toggle parsers.

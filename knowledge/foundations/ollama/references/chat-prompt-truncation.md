<!-- capsule-v2 -->
# Chat prompt truncation — how are over-context histories trimmed without dropping system or the latest message?

**Source:** Ollama MIT `main@fb30760996871fa9460115c753afd2c60d4ab0f7`; Codebase Memory `ext-ollama`. **Question:** What is the correct drop-oldest truncation that still renders a valid prompt, and how do image tokens factor in?

## chatPrompt truncate-and-render
**Path/Symbol:** `server/prompt.go:23-92` (`chatPrompt`), :94-133 (`imageTaggedMessages`), :135-157 (`renderPrompt`). **Signature:** `func chatPrompt(ctx context.Context, m *Model, tokenize tokenizeFunc, opts *api.Options, msgs []api.Message, tools []api.Tool, think *api.ThinkValue, truncate bool) (prompt string, media []llm.MediaData, _ error)`.
**Data Shape:** `tokenize` is the runner's tokenizer callback (accurate per-model counts). Images budget 768 tokens each (CLIP-seamed embedding estimate; TODO upstream: projector-aware accounting). `truncate=false` (or MLX models) skips the loop entirely.

### Decisive source
```go
for i := 0; i <= lastMsgIdx; i++ {
    // Collect system messages from the portion we're about to skip
    system = make([]api.Message, 0)
    for j := range i { if msgs[j].Role == "system" { system = append(system, msgs[j]) } }
    p, err := renderPrompt(m, append(system, msgs[i:]...), tools, think) // RENDER, not estimate
    s, err := tokenize(ctx, p)
    ctxLen := len(s)
    if m.ProjectorPaths != nil {
        for _, msg := range msgs[i:] { ctxLen += imageNumTokens * len(msg.Images) }
    }
    if ctxLen <= opts.NumCtx { currMsgIdx = i; break }
    if i == lastMsgIdx { currMsgIdx = lastMsgIdx; break }  // always ≥ last message
}
```

**Flow:** Start with the FULL message list and advance a front pointer one message at a time; every iteration re-renders the candidate window through the REAL template (system messages salvaged from the dropped prefix get re-prepended so behavior contracts survive) and tokenizes it. First fitting window wins; if none fit, keep exactly the last message. Afterward `imageTaggedMessages` rewrites `[img]` markers to positional `[img-N]` tags while collecting `llm.MediaData` (renderer-mode messages keep images unmarked for the renderer's own syntax), enforcing mllama's single-image rule on the way.
**Invariant:** Truncation granularity is whole messages; system messages from trimmed history must be preserved; the LAST message is never dropped even when it alone exceeds NumCtx (the engine handles overflow); fit is judged on rendered+tokenized bytes, never character heuristics.
**Probe:** `grep -cF "imageNumTokens := 768" server/prompt.go` → `1`; `grep -cF "currMsgIdx = lastMsgIdx" server/prompt.go` → `1`. Direct tests: `server/prompt_test.go` (606L truncation matrix, PASS at pin).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ollama", query: "chatPrompt truncate imageNumTokens", limit: 5 });
```

## Verdict
Adopt render-tokenize-advance with system salvage and last-message floor. Adapt the image token constant to your projector math; omit marker rewriting if your renderer consumes raw media arrays.

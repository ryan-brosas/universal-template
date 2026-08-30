<!-- capsule-v2 -->
# Harmony (gpt-oss) parser — how are channel headers, tool recipients, and prefill recovered from a harmony token stream?

**Source:** Ollama MIT `main@fb30760996871fa9460115c753afd2c60d4ab0f7`; Codebase Memory `ext-ollama`. **Question:** How do you parse `<|start|>assistant<|channel|>analysis|final|to=tools<|message|>…<|end|>` incrementally, including assistant-prefill continuation and TypeScript-identifier tool names?

## HarmonyParser + HarmonyMessageHandler + FunctionNameMap
**Path/Symbol:** `harmony/harmonyparser.go` (`HarmonyParser` :33-40 states LookingForMessageStart/ParsingHeader/ParsingContent; `AddImplicitStartOrPrefill` :104-118; `parseHeader` :186-241; `overlap` :243-254; `HarmonyMessageHandler.Init/Add` :396-450; `PreservedTokens` :452-462; `FunctionNameMap` :379-555). **Signature:** `func (h *HarmonyMessageHandler) Add(s string, done bool) (content, thinking string, calls []api.ToolCall, err error)` (implements `parsers.Parser`).
**Data Shape:** Tags fixed at construction: start `<|start|>`, end `<|end|>`, header-end `<|message|>`. Header grammar: role first token; `to=<name>` marks recipient ⇒ role becomes `tool`; optional `<|channel|><name>` before or after role. Events: MessageStart / HeaderComplete{Header} / ContentEmitted{Content} / MessageEnd.

### Decisive source
```go
func (s *HarmonyParser) AddImplicitStartOrPrefill(lastMessage *api.Message) {
    if lastMessage != nil && lastMessage.Role == "assistant" {
        if lastMessage.Content != "" {
            s.acc.WriteString("<|start|>assistant<|channel|>final<|message|>")   // continue final
            return
        } else if lastMessage.Thinking != "" {
            s.acc.WriteString("<|start|>assistant<|channel|>analysis<|message|>") // continue analysis
            return
        }
    }
    s.AddImplicitStart() // "<|start|>assistant"
}
// parseHeader: role "to=X" → Recipient=X, Role="tool"; channel name = run to first whitespace.
// PreservedTokens: <|start|> <|end|> <|message|> <|channel|> <|constrain|>  — but NOT <|call|>
```

**Flow:** Handler.Init seeds the accumulator with implicit-start-or-prefill BEFORE any model output so a mid-conversation request resumes in the right channel; renames every user tool to a valid TS identifier via FunctionNameMap (spaces/dots/hyphens→underscore, drop exotic runes, digit-leading gets `_`, collisions get `_2`,`_3`…; builtins `browser.*`/`python` exempt) and returns the RENAMED tools to send to the model. Streaming: content between `<|channel|>…<|message|>` and `<|end|>` is emitted through suffix-overlap buffering (identical trick to the thinking parser); `analysis` channel → thinking bucket, `final` → content, `to=` header bodies accumulate raw JSON until `done`, when exactly one tool call drains (`functions.` prefix stripped, reverse-mapped through harmonyToUser). `<|call|>` is deliberately NOT preserved — llama-server treats it as EOG and stops there.
**Invariant:** The rename maps must be consulted for EVERY tool name both directions — conversion is lossy and irreversible without `harmonyToUser`; missing reverse map falls back with a warning rather than erroring. Prefill seeding must happen in Init (per request), not construction.
**Probe:** `grep -cF "AddImplicitStartOrPrefill" harmony/harmonyparser.go` → `2` (def + Init call); `grep -cF '"unnamed"' harmony/harmonyparser.go` → `1`; `grep -cF 'case "{"' tools/tools.go` → `1`. Direct tests: `harmony/harmonyparser_test.go` `TestHeaderParsing`, `TestHarmonyParserNonStreaming`, `TestHarmonyParserStreaming`, `TestFunctionConvertAndAdd` (`go test ./harmony/` PASS at pin).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ollama", query: "HarmonyParser header channel recipient", limit: 5 });
```

## Verdict
Adopt the three-state event parser, prefill seeding, and bidirectional tool-name mapping. Adapt the tag literals only if your model family uses different frame markers; omit the TS-identifier dance if your function-name alphabet is already safe.

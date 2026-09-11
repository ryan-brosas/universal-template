<!-- capsule-v2 -->
# Generic thinking tag stream parser — how do you split <think>…</think> out of a token stream with zero re-emission?

**Source:** Ollama MIT `main@fb30760996871fa9460115c753afd2c60d4ab0f7`; Codebase Memory `ext-ollama`. **Question:** How does a streaming state machine emit thinking/content incrementally while a tag can arrive split across arbitrary chunk boundaries?

## thinking.Parser five-state eat loop
**Path/Symbol:** `thinking/parser.go:8-46` (states), :48-74 (`AddContent` loop), :77-162 (`eat`), :165-172 (`overlap`). **Signature:** `func (s *Parser) AddContent(content string) (thinking string, remaining string)`.
**Data Shape:** States: LookingForOpening → ThinkingStartedEatingWhitespace → Thinking → ThinkingDoneEatingWhitespace → ThinkingDone. Internal `acc strings.Builder` holds ONLY unemitted ambiguous bytes; the loop `for keepLooping { thinking, remaining, keepLooping = eat(s) }` drains multiple transitions per call.

### Decisive source
```go
case thinkingState_LookingForOpening:
    trimmed := strings.TrimLeftFunc(s.acc.String(), unicode.IsSpace)
    if strings.HasPrefix(trimmed, s.OpeningTag) {
        after := strings.Join(strings.Split(trimmed, s.OpeningTag)[1:], s.OpeningTag) // keep extra opens as content
        ...
    } else if strings.HasPrefix(s.OpeningTag, trimmed) {
        return "", "", false            // PARTIAL opening seen — keep accumulating
    } else if trimmed == "" {
        return "", "", false            // whitespace only — undecided
    } else {
        s.state = thinkingState_ThinkingDone
        untrimmed := s.acc.String()     // no tags at all: return ORIGINAL, whitespace intact
        s.acc.Reset()
        return "", untrimmed, false
    }
case thinkingState_Thinking:
    if overlapLen := overlap(acc, s.ClosingTag); overlapLen > 0 {   // suffix might be "<"
        thinking := acc[:len(acc)-overlapLen]                        // emit safe prefix
        s.acc.Reset(); s.acc.WriteString(acc[len(acc)-overlapLen:])  // buffer candidate
        return thinking, "", false
    }
```

**Flow:** Opening detection tolerates leading whitespace but, once past it, any non-tag content PERMANENTLY skips to ThinkingDone returning untrimmed bytes (a model that never thinks must not have its prose mangled). Inside Thinking, the closing tag is matched by longest-suffix/prefix `overlap`, holding back ≤len(tag) bytes so `</th` + `ink>` across chunks still splits cleanly. Whitespace-eating states swallow exactly one run of space between tags and content so `</think>\n\nanswer` yields clean `answer`. Callers wire it in ChatHandler only when `thinking.InferTags(m.Template.Template)` finds tags AND think=true; if the rendered prompt already ends with the opening tag the parser is pre-seeded via `AddContent(openingTag)` so the model's raw output isn't double-counted.
**Invariant:** Never emit bytes that could later prove to be part of a tag; on skip-to-done return UNTRIMMED original text; buffer reset must accompany every state transition or already-emitted text replays (regression pinned by TestThinkingStreaming).
**Probe:** `grep -cF "thinkingState_ThinkingDoneEatingWhitespace" thinking/parser.go` → `4`; `grep -cF "func overlap(s, delim string) int" thinking/parser.go` → `1`. Direct tests: `thinking/parser_test.go` `TestExtractThinking` + `TestThinkingStreaming` (`go test ./thinking/` PASS at pin).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ollama", query: "thinking Parser AddContent eat state", limit: 5 });
```

## Verdict
Adopt the five-state machine + suffix-overlap buffering wholesale — it is runner-agnostic pure string logic. Adapt tag inference (InferTags walks the Go template AST for `.Thinking` fields) to your template store; nothing to omit.

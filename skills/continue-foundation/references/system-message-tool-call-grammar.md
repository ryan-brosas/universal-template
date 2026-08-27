<!-- capsule-v2 -->
# System-message tool-call grammar — how do models WITHOUT native tool-calling invoke tools through parsed markdown code blocks?

**Source:** continue Apache-2.0 `main@5522c6f44ca0ac3528b37244818fbfa39b5af470`; Codebase Memory `continue`. **Question:** How does a porter give the non-native-tool half of the model zoo a reliable function-call protocol over plain text streaming?

## Encode tools into the system message; intercept the stream with a hold-back buffer; parse a line-indexed fence grammar into native-shaped deltas

**Path/Symbol:** `core/tools/systemMessageTools/`: `detectToolCallStart.ts` whole (30L), `types.ts:31–51` (`ToolCallParseState`/`getInitialToolCallParseState`), `interceptSystemToolCalls.ts` whole (119L), `toolCodeblocks/index.ts` whole (127L, `acceptedToolCallStarts` :9–12), `toolCodeblocks/parseSystemToolCall.ts` whole (121L, `handleToolCallBuffer` :11–121), `buildToolsSystemMessage.ts` whole (82L), `convertSystemTools.ts` whole (81L), `systemToolUtils.ts` whole (38L); activation gate `gui/src/redux/thunks/streamNormalInput.ts:112–119` + `core/llm/toolSupport.ts:513–523`.
**Signature:** `interceptSystemToolCalls(messageGenerator, abortController, framework): AsyncGenerator<ChatMessage[], PromptLog | undefined>`; `handleToolCallBuffer(chunk: string, state: ToolCallParseState): ToolCallDelta | undefined`.
**Data Shape:** wire grammar per call: ` ```tool\nTOOL_NAME: <name>\nBEGIN_ARG: <arg>\n<value lines>\nEND_ARG\n…\n``` `; parse state is line-indexed `{lineChunks[][], currentLineIndex, currentArgName, currentArgChunks[], processedArgNames Set, done}`; output is standard `ToolCallDelta`s (name delta, then arg-prefix deltas `{"arg":`, then value deltas, then `}`) so downstream consumers cannot tell them from native calls.

### Decisive source
```ts
// poor-model normalization — accepted starts, index 0 is canonical:
acceptedToolCallStarts = [["```tool\n", "```tool\n"], ["tool_name:", "```tool\nTOOL_NAME:"]];
// detectToolCallStart: case-insensitive match; strict prefixes ⇒ HOLD the chunk back;
// i !== 0 hits get regex-replaced into canonical form before parsing.
// handleToolCallBuffer: line-indexed switch — NOTE case 0 FALLS THROUGH into case 1,
// merging a fence line that swallowed the name line:
case 1: if (isNewLine) {
  const name = (line.split(/tool_?name:/i)[1] ?? "").trim();
  if (!name) throw new Error("Invalid tool name");
  return createDelta(name, "", state.toolCallId);
}
// args collected WHOLE deliberately ("support for JSON booleans is tricky otherwise");
// raw newlines inside quoted strings escaped BEFORE JSON.parse, only when value starts [ or {:
trimmedValue = trimmedValue.replace(/"((?:\\[\s\S]|[^"\\])*?)"/g, (m) =>
  '"' + m.slice(1, -1).replace(/([^\\])\n/g, "$1\\n").replace(/^\n/g, "\\n") + '"');
const parsed = JSON.parse(trimmedValue);          // try
return createDelta("", JSON.stringify(parsed), id); // catch ⇒ JSON.stringify(trimmedValue)
```

**Flow:** activation: `experimental.onlyUseSystemMessageTools ? false : modelSupportsNativeTools(model)` — capability flag first, provider regex allowlist second (gemini/gpt/claude/grok families), unknown provider ⇒ false; when false, tools are rendered INTO the system message inside `<tool_use_instructions>`: predefined-message tools get full EXAMPLE CALLS, dynamic tools get ```tool_definition blocks plus one shared example; conversion failures per tool are console.error non-fatal. Streaming: chunks split on /(```|\n)/ so fences and newlines arrive alone; `interceptSystemToolCalls` skips non-assistant messages, native-toolcall messages, and image parts; holds back any chunk that is a strict prefix of an accepted start; feeds the rest to the line machine; after `done`, state resets so trailing prose or ANOTHER tool call flows normally. Stream-end repair: an incomplete-but-started arg list synthesizes a closing `}` delta (:34–44). History replay (`convertToolCallStatesToSystemCallsAndOutput`): past native toolCalls are re-rendered BACK to text blocks in the assistant message and a synthesized USER message carries "Tool output for \<name\> tool call:" + rendered output with cancelled/no-output sentinels (TODO comment: ids confuse dumb models).
**Invariant:** the protocol's contract is bidirectional round-tripping through ONE text grammar — definitions out, calls in, history re-rendered back — so model-visible syntax never forks between request and replay. Arg values parse-or-stringify but never fail the stream; the only throws ("Invalid tool name"/"Invalid begin arg line") mark grammar violations mid-stream.
**Probe:** `toolCodeblocks/parseSystemToolCall.vitest.ts` (whole 281L, 12 cases): fence+name merge via fall-through, case-insensitive TOOL_NAME/BEGIN_ARG/END_ARG, arg collection, numeric "123" stays unquoted, multi-arg comma prefixing, finalize `}` on closing fence OR newline, and the SEARCH/REPLACE-diff case proving quoted-raw-newline escaping survives JSON.parse (:250–280). `toolCodeblocks/interceptSystemToolCalls.vitest.ts` (whole 423L — co-located under toolCodeblocks/, NOT beside the interceptor): end-to-end delta sequences for fenced AND bare `TOOL_NAME:` starts, content preserved after the call, mid-message calls, abort stop, boolean/number args.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "continue", query: "system message tool call detection fence buffer intercept args streaming", limit: 14 });
```

## Verdict
Adopt the text-grammar-with-native-deltas approach for non-tool-trained models, the hold-back prefix buffer, and whole-arg collection before JSON.parse; adapt the start vocabulary to your prompt format; omit the history-replay renderer if your client keeps native tool messages. Trap: the case-0→case-1 fall-through is load-bearing (bare `TOOL_NAME:` starts rely on it after normalization rewrites the buffer) — refactoring it to separate cases silently breaks the no-fence path that poor models actually emit.

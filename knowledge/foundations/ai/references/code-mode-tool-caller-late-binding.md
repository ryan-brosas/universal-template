<!-- capsule-v2 -->
# Code-mode tool-caller late binding — experimental_toolCaller bind and the direct-call marker

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f...`; Codebase Memory `ai`. **Question:** How does one `code_mode` tool in the model's tool list gain access to the OTHER tools passed to the same generate call?

## Two factories, one binding seam
**Path/Symbol:** `packages/code-mode/src/code-mode-tool.ts` whole (:20–60); marker `packages/code-mode/src/direct-tool-call.ts:6`; consumer contract in generate-text (`experimental_toolCallers` map + per-tool caller assignment).
**Signature:** `createCodeModeTool(tools, options)` → standalone Tool with `{js:string}` inputSchema; `codeModeTool(options)` → `experimental_toolCaller(createCodeModeTool({}, options), {type:'local', bind: tools => createCodeModeTool(tools, options)})`.
**Data Shape:** tool description is generated TWICE — empty at construction (placeholder), regenerated inside `bind` with the real bound set.

### Decisive source
```ts
return experimental_toolCaller(createCodeModeTool({}, options), {
  type: 'local',
  bind: tools => createCodeModeTool(tools as unknown as CodeModeToolSet, options),
});
```

**Flow:** app passes `tools: { code_mode: codeModeTool(), add: tool({...}) }` + `experimental_toolCallers: { add: ['code_mode'] }` → the generation loop hands the NON-caller tools to every registered caller's `bind` before dispatch → model sees exactly one `code_mode` entry whose description now declares `add`'s real signature; when it emits a code_mode call, execute runs sandboxed source that can invoke `tools.add`. Direct test pins the wire shape: mock doGenerate receives `options.tools?.map(t => t.name)` equal to `['code_mode']` ONLY (:198), while the result still resolves `{sum: 10}` from the nested add (:244). `DIRECT_TOOL_CALL = 'AI_SDK_DIRECT_TOOL_CALL'` is a deliberately JSON-serializable string marker letting a model bypass code-mode for a single direct invocation.
**Invariant:** the bound toolset excludes callers themselves — a porter who feeds the full map into bind creates recursive code-mode-in-code-mode. Late binding means the description the MODEL reads differs from the placeholder built at factory time; anything cached from construction time is stale.
**Probe:** deterministic (repo root): `grep -nF 'experimental_toolCaller' packages/code-mode/src/code-mode-tool.ts` → lines `2:`+`55:`; `grep -nF 'AI_SDK_DIRECT_TOOL_CALL' packages/code-mode/src/direct-tool-call.ts packages/code-mode/src/tool-invocation.test.ts` → 3 lines (src :6, test :14/:15); test anchors tool-invocation.test.ts:238 (`experimental_toolCallers: {`) and :244 (`toolResults[0]?.output).toEqual({ sum: 10 })`).
**Retrieve:** `await mcp.codebase_memory.search_graph({ project: "ai", query: "createCodeModeTool experimental_toolCaller bind", limit: 3 });` // verified live @9d9a73f: createCodeModeTool :20-46 rank#1, bind :57-58 rank#2

## Verdict
Adopt local-caller bind semantics (bind receives peers, not self); adapt naming/registration to your generation loop; omit the worker-pool internals of `run` (setMaxWorkers external).

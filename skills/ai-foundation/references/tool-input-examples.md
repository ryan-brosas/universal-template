<!-- capsule-v2 -->
# addToolInputExamplesMiddleware — how do you give example tool inputs to providers whose wire format has no native examples field?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory project `ai`. **Question:** Where do serialized examples go, when is the original property removed, and which tools are left untouched?

## addToolInputExamplesMiddleware
**Path/Symbol:** `packages/ai/src/middleware/add-tool-input-examples-middleware.ts:addToolInputExamplesMiddleware` (:31–90).
**Signature:** `function addToolInputExamplesMiddleware({ prefix = 'Input Examples:', format = defaultFormatExample, remove = true } = {}): LanguageModelMiddleware` — hook: `transformParams: async ({ params }) => params'`.
**Data Shape:** Targets only `tool.type === 'function' && tool.inputExamples?.length` (provider tools and empty-example arrays pass through untouched). Example section = `` `${prefix}\n${formattedExamples.join('\n')}` `` appended to `description` after a blank line (`\n\n`) when a description already exists; default formatter is `JSON.stringify(example.input)`.

### Decisive source
```ts
transformParams: async ({ params }) => {
  if (!params.tools?.length) return params;
  const transformedTools = params.tools.map(tool => {
    // Only transform function tools that have inputExamples
    if (tool.type !== 'function' || !tool.inputExamples?.length) return tool;
    const formattedExamples = tool.inputExamples
      .map((example, index) => format(example, index))
      .join('\n');
    const examplesSection = `${prefix}\n${formattedExamples}`;
    const toolDescription = tool.description
      ? `${tool.description}\n\n${examplesSection}`   // blank-line join, not inline
      : examplesSection;
    return { ...tool, description: toolDescription,
             inputExamples: remove ? undefined : tool.inputExamples };
  });
  return { ...params, tools: transformedTools };
},
```

**Flow:** transformParams runs during param assembly (before provider serialization, before wrap hooks) → per-tool conditional rewrite → providers that ignore unknown fields see only the enriched description; `remove:true` keeps the request clean for strict providers.
**Invariant:** The middleware must be lossless-by-default: with defaults, no `inputExamples` field survives on the wire and every example is recoverable from the description. Tools without examples must remain byte-identical (no `description` key churn) so provider-side tool-definition caching stays stable.
**Probe:** `packages/ai/src/middleware/add-tool-input-examples-middleware.test.ts` — append :16, no existing description :66, custom prefix/format :111/:146/:180, remove true/false :220/:246, pass-through for no/empty/provider tools :284/:325/:351.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "addToolInputExamplesMiddleware", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt the description-append + strip pattern for hosts targeting strict providers. Adapt the prefix text and formatter to host conventions; keep `remove` configurable — some providers tolerate the extra field and keeping it preserves structure. Coverage caveat: best-effort index; excerpts read directly at HEAD.

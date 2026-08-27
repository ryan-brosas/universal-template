<!-- capsule-v2 -->
# Request-side tool assembly — how does the user's tool map become the ordered provider tool array, including description resolution and partial ordering?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory `ai`. **Question:** How are function/dynamic/provider tools converted to wire tools, in what order, and what exactly is sent when a tool has no description?

## prepareTools + prepareToolChoice
**Path/Symbol:** `packages/ai/src/prompt/prepare-tools.ts:15-80` (`prepareTools`), `:82-106` (`orderToolEntries`), `:108-127` (`resolveToolDescription`); `packages/ai/src/prompt/prepare-tool-choice.ts:4-15` (`prepareToolChoice`).
**Signature:** `prepareTools({tools?, toolOrder?: ReadonlyArray<keyof TOOLS & string> | undefined, toolsContext?, experimental_sandbox?}): Promise<Array<LanguageModelV4FunctionTool | LanguageModelV4ProviderTool> | undefined>`; `prepareToolChoice({toolChoice}): LanguageModelV4ToolChoice`.
**Data Shape:** In: ToolSet (name→tool object), optional partial order list, per-tool runtime context, sandbox session. Out: wire tool array or `undefined` (no tools).

### Decisive source
```ts
if (!isNonEmptyObject(tools)) return undefined;      // {} and undefined both ⇒ NO tools field

switch (toolType) {
  case undefined:
  case 'dynamic':
  case 'function': {                                  // untyped tools default to function
    const description = resolveToolDescription({ tool, toolName: name, toolsContext,
      experimental_sandbox: sandbox });
    languageModelTools.push({
      type: 'function' as const, name,
      inputSchema: await asSchema(tool.inputSchema).jsonSchema,
      ...(description != null ? { description } : {}),
      ...(inputExamples != null ? { inputExamples } : {}),
      ...(providerOptions != null ? { providerOptions } : {}),
      ...(strict != null ? { strict } : {}),
    });
    break;
  }
  case 'provider':
    languageModelTools.push({ type: 'provider' as const, name, id: tool.id, args: tool.args });
    break;
  default: { const exhaustiveCheck: never = toolType as never; throw ...; }
}

// orderToolEntries with a PARTIAL toolOrder: listed tools first in given order,
// everything else appended ALPHABETICALLY — and duplicates in toolOrder do NOT duplicate tools
const orderedTools   = toolEntries.filter(([n]) => toolOrder.includes(n))
  .sort(([a], [b]) => toolOrder.indexOf(a) - toolOrder.indexOf(b));
const unorderedTools = toolEntries.filter(([n]) => !toolOrder.includes(n))
  .sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0));
```

**Flow:** empty-check → iterate ordered entries → three-way type dispatch (`undefined|dynamic|function` all become `type:'function'`; `provider` passes `{id, args}` through) → schema converted via `asSchema(...).jsonSchema` at request time → description may be a FUNCTION resolved per-call with `{context: toolsContext[toolName], experimental_sandbox}`. Choice side: absent ⇒ `{type:'auto'}`; string passthrough (`auto|none|required|any` per host dialect); object ⇒ `{type:'tool', toolName}`.

**Invariant:** Absent tools means the key is OMITTED from the request entirely — an empty array is never sent (test-pinned). Ordering is deterministic even for unordered tools (alphabetical), so prompt caching sees stable tool lists across requests when the set is unchanged. `toolOrder` is a hint over the SET, never a filter or a duplicator.

**Probe:** `packages/ai/src/prompt/prepare-tools.test.ts:37` ("returns undefined when tools are not provided"), `:127` (partial order: `['middle']` ⇒ `[middle, alpha, providerTool, zebra]`), `:155` (order preserved then alpha tail), `:181` (duplicate `'tool2','tool2'` ⇒ no duplication), `:300` (description function receives context+sandbox); `packages/ai/src/prompt/prepare-tool-choice.test.ts` (absent ⇒ auto mapping).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "prepareTools orderToolEntries resolveToolDescription", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: omit-not-empty-array, untyped-tool-defaults-to-function, dynamic alphabetical fallback for unordered tools, partial-order semantics, per-call functional descriptions. Adapt the provider-tool `{id,args}` envelope and choice vocabulary to your spec version.

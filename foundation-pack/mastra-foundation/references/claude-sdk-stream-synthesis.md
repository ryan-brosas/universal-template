<!-- capsule-v2 -->
# claude-sdk-stream-synthesis

## Source
- Repo: `mastra`
- Path: `agent-sdks/claude/src/utils.ts`
- Symbol: `createCompletedMastraStream` / `createNoopModel`
- Lines: 58-130
- Commit: `3d2ff0d0a959792331f7cfb12dab6d08506676e7`
- Graph Node: `ext-mastra.agent-sdks.claude.src.utils.createCompletedMastraStream`

## Signature & Data Shape
```typescript
export function createCompletedMastraStream(params: {
  runId: string;
  prompt: string;
  text: string;
  responseId: string;
  modelId: string;
  usage: LanguageModelUsage;
  providerMetadata?: ProviderMetadata;
  costContext?: CostContext;
  object?: unknown;
}): ReadableStream<ChunkType>;
```

## Decisive Source Excerpt
```typescript
export function createNoopModel({ modelId, provider }: { modelId: string; provider: string }): MastraLanguageModel {
  return {
    modelId,
    provider,
    specificationVersion: 'v3',
    supportedUrls: {},
    doGenerate: async () => createNoopStreamResult(),
    doStream: async () => createNoopStreamResult(),
  } as MastraLanguageModel;
}

export function createCompletedMastraStream({
  runId,
  prompt,
  text,
  responseId,
  modelId,
  usage,
  providerMetadata,
  costContext,
  object,
}: {
  runId: string;
  prompt: string;
  text: string;
  responseId: string;
  modelId: string;
  usage: LanguageModelUsage;
  providerMetadata?: ProviderMetadata;
  costContext?: CostContext;
  object?: unknown;
}): ReadableStream<ChunkType> {
  return new ReadableStream<ChunkType>({
    start(controller) {
      const textId = randomUUID();
      enqueueStartChunks(controller, { responseId, modelId });
      enqueueTextDelta(controller, { textId, text });
      enqueueFinishChunks(controller, {
        usage,
        providerMetadata,
        costContext,
        object,
      });
      controller.close();
    },
  });
}
```

## Flow
1. Instantiate web-standard `ReadableStream<ChunkType>` container.
2. Emit header chunks (`response-metadata`, `stream-start`) using resolved `responseId` and `modelId`.
3. Emit body payload (`text-start`, `text-delta`, `text-end`) tagged with a freshly generated `textId`.
4. Emit terminal envelope (`finish` chunk) containing calculated token usage, provider metadata, cost context, and structured object.
5. Close stream controller to finalize downstream consumption.

## Invariant
Completed LLM response streams must follow the strict 3-phase chunk sequence (Start $\to$ TextDelta $\to$ Finish with Usage and CostContext) to satisfy streaming protocol consumers when synthesizing synthetic or cached model turns.

## Direct-Test Probe
- File: `agent-sdks/claude/src/__tests__/utils.test.ts`
- Lines: 25-60
- Suite: `describe('createCompletedMastraStream')`

## Graph Query
```bash
codebase-memory-mcp cli search_graph '{"project":"ext-mastra","query":"createCompletedMastraStream enqueueStartChunks enqueueFinishChunks"}'
```

## Verdict
Adopt the standard completed stream synthesis helper and 3-phase chunk emitter.

<!-- capsule-v2 -->
# agent-relevance-scorer

## Source
- Repo: `mastra`
- Path: `packages/rag/src/rerank/relevance/mastra-agent/index.ts`
- Symbol: `MastraAgentRelevanceScorer` / `parseRelevanceScore`
- Lines: 6-53
- Commit: `3d2ff0d0a959792331f7cfb12dab6d08506676e7`
- Graph Node: `ext-mastra.packages.rag.src.rerank.relevance.mastra-agent.MastraAgentRelevanceScorer.getRelevanceScore`

## Signature & Data Shape
```typescript
export function parseRelevanceScore(responseText: string): number;

export class MastraAgentRelevanceScorer implements RelevanceScoreProvider {
  constructor(name: string, model: MastraLanguageModel | MastraLegacyLanguageModel);
  getRelevanceScore(query: string, text: string): Promise<number>;
}
```

## Decisive Source Excerpt
```typescript
function parseRelevanceScore(responseText: string): number {
  const trimmed = responseText.trim();
  const score = Number(trimmed);

  if (!trimmed || !Number.isFinite(score) || score < 0 || score > 1) {
    throw new Error(`Invalid relevance score returned by model: ${responseText}`);
  }

  return score;
}

export class MastraAgentRelevanceScorer implements RelevanceScoreProvider {
  private agent: Agent;

  constructor(name: string, model: MastraLanguageModel | MastraLegacyLanguageModel) {
    this.agent = new Agent({
      id: `relevance-scorer-${name}`,
      name: `Relevance Scorer ${name}`,
      instructions: `You are a specialized agent for evaluating the relevance of text to queries.
Your task is to rate how well a text passage answers a given query.
Output only a number between 0 and 1, where:
1.0 = Perfectly relevant, directly answers the query
0.0 = Completely irrelevant
Consider:
- Direct relevance to the question
- Completeness of information
- Quality and specificity
Always return just the number, no explanation.`,
      model,
    });
  }

  async getRelevanceScore(query: string, text: string): Promise<number> {
    const prompt = createSimilarityPrompt(query, text);
    const model = await this.agent.getModel();
    let response;

    if (isSupportedLanguageModel(model)) {
      response = await this.agent.generate(prompt);
    } else {
      response = await this.agent.generateLegacy(prompt);
    }

    return parseRelevanceScore(response.text);
  }
}
```

## Flow
1. Construct specialized relevance-evaluator agent configured with pure numerical output instructions.
2. Render evaluation prompt from `createSimilarityPrompt(query, text)`.
3. Dispatch model generation through standard or legacy model provider adapter.
4. Clean and parse numerical text with `parseRelevanceScore`.
5. Strictly validate: reject empty responses, non-finite values, and numbers outside `[0.0, 1.0]`.

## Invariant
Reranking score parsers must reject any non-numeric commentary or out-of-range floats (`score < 0 || score > 1 || !Number.isFinite(score)`), failing fast before corrupted scores reach the ranking sort algorithm.

## Direct-Test Probe
- File: `packages/rag/src/rerank/relevance/mastra-agent/index.test.ts`
- Lines: 20-55
- Suite: `describe('MastraAgentRelevanceScorer')`

## Graph Query
```bash
codebase-memory-mcp cli search_graph '{"project":"ext-mastra","query":"MastraAgentRelevanceScorer parseRelevanceScore"}'
```

## Verdict
Adopt the prompt-engineered LLM relevance scorer and strict bounded float parser.

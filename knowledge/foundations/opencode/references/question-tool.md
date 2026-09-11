<!-- capsule-v2 -->
# Question tool — ask the user mid-turn

**Source:** opencode MIT `<branch>@<commit>`; Codebase Memory `opencode`. **Question:** how does a coding agent pause and ask the user questions mid-turn?

## Connected graph-selected seam
**Path/Symbol:** `packages/opencode/src/tool/question.ts` (44 lines): `Parameters` (:6-9), `QuestionTool` (:14), `execute` (:17-24).
**Signature:** `execute({questions}, ctx)` — `question.ask({questions})` returns the user's answers.
**Data Shape:** `Parameters = {questions: Question.Prompt[]}` (mutable array); output = the user's answers.

### Decisive source
```ts
export const Parameters = Schema.Struct({
  questions: Schema.mutable(Schema.Array(Question.Prompt)).annotate({ description: "Questions to ask" }),
})
// QuestionTool.execute -> const answers = yield* question.ask({ questions })
```

**Flow:** the model calls `question` with one or more prompts; the tool asks the user and returns the answers so the model can continue.
**Invariant:** questions are a mutable array (can ask several at once); the tool suspends until the user answers.
**Probe:** `packages/opencode/test/tool/question.test.ts` (single/multiple questions; answers returned).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "QuestionTool question ask answers prompts", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the mid-turn user-question tool (ask several prompts, return answers); adapt the prompt/answer shape to host.

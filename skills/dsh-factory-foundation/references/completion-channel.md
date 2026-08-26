<!-- capsule-v2 -->
# Completion channel — how does a model report completion without the scheduler ever trusting intent?

**Source:** dsh-factory MIT `main@3405edc7`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-dsh-factory`. **Question:** How do I give an LLM agent an explicit completion tool that cannot lie, fire early, or double-report?

## factory_finish tool + consume/pending channel
**Path/Symbol:** `packages/tools/src/index.ts` (`installFactoryCompletionTool`, `FactoryCompletionChannel`) (:86–128).
**Signature:** `export function installFactoryCompletionTool(ctx: Context): FactoryCompletionChannel`; channel = `{ consume(): FactoryFinishReport | undefined; pending(): boolean }`.
**Data Shape:** closure-scoped single-slot `report: FactoryFinishReport | undefined`; tool params `{ outcome: 'succeeded'|'failed'|'blocked', summary, details?, artifacts? }`.

### Decisive source
```ts
const sharesQuestionStep = exec.agent?.session.events.some(event =>
    (location !== undefined
      && event.type === 'assistant/message'
      && event.data.turn === location.turn
      && event.data.step === location.step
      && event.data.message.content.some(block => block.type === 'tool-call' && block.name === 'ask_user_question'))
    || (event.type === 'tool/code-dispatch-start'
      && event.data.rootCallId === exec.rootCallId
      && event.data.name === 'ask_user_question')) === true
if (sharesQuestionStep) {
    throw new Error('factory_finish must be called in a later model step after ask_user_question returns; ...')
}
if (report !== undefined) throw new Error('factory_finish already has a report pending for this turn')
```

**Flow:** tool registered per Agent scope → model calls `factory_finish` → same-step/same-code-root check against `ask_user_question` (a human question in THIS step or code root rejects the finish) → duplicate check (second call errors) → buffer report → scheduler's monitor consumes it exactly once after the turn settles (`consume()` reads and clears). `blocked` reports route to `markRunWaiting` — the node stays nonterminal awaiting the human answer.
**Invariant:** Completion is data, never inference: the scheduler commits only what the tool buffered, only after idle, and never in the same model step as the human question. The human-gate is enforced by scanning session events for the question's turn/step/code-root — not by prompt discipline alone.
**Probe:** `packages/tools/tests/completion.spec.ts` "rejects completion from the same native step or run_code root as a human question" (same-step finish → isError, error text contains "later model step after ask_user_question returns"; same-code-root → isError; later step accepted). Deterministic from repo root: `grep -c 'later model step after ask_user_question returns' packages/tools/src/index.ts` = 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-dsh-factory", query: "FactoryFinishReport", limit: 5, fields: ["signature", "name", "file"] });
```
(CLI equivalent verified live: rank-1 `FactoryFinishReport Interface packages/protocol/src/types.ts 438-443`.)

## Verdict
Adopt the explicit-completion-channel pattern with the anti-premature-finish event scan. Adapt tool registration API to the host tool runtime. Omit presentCall card rendering (UI concern).

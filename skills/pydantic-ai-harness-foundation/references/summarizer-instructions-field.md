<!-- capsule-v2 -->
# Summarizer instructions field: the nested summary request's system-prompt surface (#669)

## Source / Question
`pydantic_ai_harness` (MIT) `main@76db3dec`; Codebase Memory project `pydantic-ai-harness`. **Question:** The nested summary request inside `SummarizingCompaction` has TWO prompt surfaces — which one becomes the request's system prompt, and why must that surface stay a field for endpoints like Claude Code OAuth that reject requests whose first system block is not a fixed instruction string? (Pass-7 repair: the original citation named the since-retired slugged twin project and a checkout path under `inspo/frameworks/`; both re-pointed to the canonical project/root, which serve the identical head.)

## Path / Symbol
`compaction/_summarizing_compaction.py` — module constant `_DEFAULT_INSTRUCTIONS` (:89–91); field `SummarizingCompaction.instructions: str = field(default=_DEFAULT_INSTRUCTIONS, kw_only=True)` (:319–325); sole consumption site inside `_summarize` (:637–640); contrast surface `summary_prompt: str = _DEFAULT_SUMMARY_PROMPT` (:313–317) consumed at :617.

## Signature
```python
instructions: str = field(default=_DEFAULT_INSTRUCTIONS, kw_only=True)
# ...
agent: Agent[None, str] = Agent(
    cast('Model[Any] | str', model),
    instructions=self.instructions,
)
result = await agent.run(prompt, usage=ctx.usage, usage_limits=reserved_usage_limits(ctx.usage_limits))
return result.output.strip()
```

## Data Shape
Two disjoint prompt surfaces on one strategy: `summary_prompt` shapes the USER turn (`prompt = self.summary_prompt.format(messages=formatted)` at :617, plus the optional `<previous-summary>` anchor block at :619–623); `instructions` sets the internal one-shot Agent's STATIC instructions, which pydantic-ai sends as the request's SYSTEM prompt. The default reproduces the pre-#669 hardcoded string byte-for-byte (`'You are a context summarization assistant. Extract the most important information from conversations.'`), so behavior is unchanged unless the field is set. `kw_only=True` keeps positional constructor compatibility for pre-drift call sites (commit's "preserve summarizer constructor compatibility").

### Decisive source
```python
_DEFAULT_INSTRUCTIONS = (
    'You are a context summarization assistant. Extract the most important information from conversations.'
)
```
(:89–91) and the consumption site (:637–640):
```python
        agent: Agent[None, str] = Agent(
            cast('Model[Any] | str', model),
            instructions=self.instructions,
        )
```
The field docstring states the contract directly (:320–325): "`summary_prompt` shapes the user turn of the summary request; this sets the internal agent's static instructions, which Pydantic AI sends in the request's system prompt. Override it when the summarizer endpoint requires a fixed leading instruction."

**Flow:** `_summarize` formats the user turn from `summary_prompt` (+ anchored increment when a previous summary exists) → realtime-model guard refuses non-request-response models with a loud `UserError` demanding an explicit `model=` (:629–634) → builds a fresh one-shot `Agent(model, instructions=self.instructions)` → runs with parent-folded usage and reserved request limits (:641) → `.strip()`s the output. The field survives dataclass copies (`with_focus` uses `replace()` on `summary_prompt` only, :386–394) and every construction path feeds it verbatim into the Agent.

**Invariant:** Exactly one system-prompt surface per strategy: user-turn shaping lives ONLY in `summary_prompt`; system-prompt shaping lives ONLY in `instructions`. Never hardcode either back or merge them — an endpoint that constrains the first system block cannot use `SummarizingCompaction` at all unless `instructions` stays overridable, and the default must equal the historical hardcoded string so unset behavior never drifts.

**Probe:** `bash -c 'cd /mnt/hdd/utopia/inspo/pydantic-ai-harness && /tmp/harness-p6-venv/bin/python -m pytest "tests/compaction/test_compaction.py::TestSummarizingCompactionModel::test_summarizer_agent_gets_the_default_instructions" "tests/compaction/test_compaction.py::TestSummarizingCompactionModel::test_instructions_override_reaches_the_summarizer_agent" -q'` — both assert `MockAgent.call_args.kwargs['instructions']` equals the field/default (:2145–2158, :2161–2179); EXECUTED GREEN 2/2 at pin `76db3dec` (re-executed at the canonical root during pass 7; see work-record verification.md).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pydantic-ai-harness", query: "_DEFAULT_INSTRUCTIONS SummarizingCompaction instructions summarizer", limit: 3 });
```
CLI-equivalent verified live (rank#1 default-instructions test :2145–2158, rank#3 override test :2161–2179).

## Verdict
**Adopt** the two-surface prompt split for any nested LLM helper: a `{messages}` user-turn template plus a separately overridable static system-instruction field whose default preserves legacy behavior exactly. **Adopt** the kw-only field addition pattern when widening a public dataclass constructor post-hoc. **Adapt** the default wording to your domain. **Omit** pydantic-ai's specific `Agent`/instructions plumbing if your host injects system prompts through a different mechanism — the invariant (one overridable surface per prompt role) is the portable part.

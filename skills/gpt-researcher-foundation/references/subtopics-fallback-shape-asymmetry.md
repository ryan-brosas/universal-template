<!-- capsule-v2 -->
# Subtopic planning fallback shape asymmetry — how does subtopic construction degrade on LLM failure, and what type mismatch must consumers guard?

**Source:** gpt-researcher Apache-2.0 `main@5d84d2f5553e70a2765a8ff3a0d2672d60437ce8`; Codebase Memory `gpt-researcher`. **Question:** When porting structured-output planning (LLM → validated model), what does the failure path return, and why does the consumer only survive it by accident of an empty default?

## construct_subtopics Pydantic chain + raw-list fallback
**Path/Symbol:** `gpt_researcher/utils/llm.py:155-217` (`construct_subtopics`), `gpt_researcher/utils/validators.py:17-28` (`Subtopics`/`Subtopic`), `backend/report_type/detailed_report/detailed_report.py:98-109` (`_get_all_subtopics`, consumer).
**Signature:** `async def construct_subtopics(task: str, data: str, config, subtopics: list = [], prompt_family=PromptFamily, **kwargs) -> list` — the annotation says `list` but the SUCCESS path returns a `Subtopics` pydantic model.
**Data Shape:** success = `Subtopics(subtopics=[Subtopic(task=str), ...])` via LangChain chain `prompt | model | PydanticOutputParser(pydantic_object=Subtopics)`; failure = the ORIGINAL `subtopics` argument (a plain list). Provider kwargs: `reasoning_effort=High` when `config.smart_llm_model in SUPPORT_REASONING_EFFORT_MODELS`, else `temperature=config.temperature`; always `max_tokens=config.smart_token_limit`.

### Decisive source
```python
# llm.py:177-217 — success returns the parsed MODEL, failure returns the input LIST
    try:
        parser = PydanticOutputParser(pydantic_object=Subtopics)
        ...
        provider_kwargs = {'model': config.smart_llm_model}
        if config.smart_llm_model in SUPPORT_REASONING_EFFORT_MODELS:
            provider_kwargs['reasoning_effort'] = ReasoningEfforts.High.value
        else:
            provider_kwargs['temperature'] = config.temperature
        ...
        output = await chain.ainvoke({...}, **kwargs)
        return output
    except Exception as e:
        logging.getLogger(__name__).error("Exception in parsing subtopics: %s", e, exc_info=True)
        return subtopics
```
```python
# detailed_report.py:99-107 — consumer assumes the model shape; safe ONLY while fallback is falsy
    subtopics_data = await self.gpt_researcher.get_subtopics()
    all_subtopics = []
    if subtopics_data and subtopics_data.subtopics:
        for subtopic in subtopics_data.subtopics:
            all_subtopics.append({"task": subtopic.task})
    else:
        print(f"Unexpected subtopics data format: {subtopics_data}")
```

**Flow:** writer.get_subtopics (:206-234) forwards researcher.query/context/subtopics into construct_subtopics → Pydantic-parsed Subtopics on success → DetailedReport._get_all_subtopics projects to `[{"task": ...}]` dicts for the per-subtopic loop. On ANY exception (provider error, parse error, even a config attribute error) the original `subtopics` list comes back; DetailedReport never passes non-empty subtopics into its main researcher, so the fallback is `[]` → falsy → the `else` branch prints "Unexpected subtopics data format" and the loop runs over zero subtopics.
**Invariant:** a structured-output planner's failure path must return something the consumer can truthiness-test BEFORE attribute access — here the type asymmetry (model vs list) is masked only by the empty default. A host that passes non-empty seed subtopics would hit `AttributeError: 'list' object has no attribute 'subtopics'` on the failure path (latent defect at this pin, same class as empty-descent-unbound-bug). The error log must interpolate the real exception (`%s", e` with exc_info) — upstream regressed once on a non-f-string that logged the literal text "{e}".
**Probe:** `tests/test_construct_subtopics_error_log.py` (55L, executed-read GREEN) pins BOTH halves with a `_BrokenConfig` whose `__getattr__` raises: result == the passed-in fallback list, AND caplog contains "boom-sentinel-12345" but NOT "{e}". Runner BLOCKED in-lane (missing aiofiles, read-only checkout) — test body verified line-exact instead. Byte anchors: llm.py:192-196 (reasoning gate), :204-211 (chain invoke + model return), :213-217 (list fallback); detailed_report.py:102 (attribute access).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "gpt-researcher", query: "construct_subtopics Subtopics PydanticOutputParser subtopics fallback", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the degrade-to-input pattern (planner failure returns the caller's seed so planning never blocks the pipeline) and the test technique of forcing the except branch via a raising config stand-in. Adapt the reasoning-effort-vs-temperature gate to your provider table. Omit nothing from the consumer guard when porting: normalize the fallback to the SAME type as success (e.g. wrap the list in the model) or keep the truthiness-before-attribute-access order — the current asymmetry is a latent crash, not a design to copy.

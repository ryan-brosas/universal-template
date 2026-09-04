<!-- capsule-v2 -->
# LLM dataset generation — how do you make an LLM generate a dataset file that the SAME loader will accept?

**Source:** pydantic-ai MIT `main@a5b5fb7a247f863599d61dfa9159bc2ebc786255` (pydantic_evals); Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** A porter adding "generate example eval data for me" needs an LLM to emit a dataset conforming to the user's generic Case/Dataset types — but the generated artifact must round-trip through the EXISTING loader (registry resolution, $schema handling), not a parallel construction path, and models routinely wrap JSON in markdown fences despite instructions.

## Schema-in-prompt + str output + fence strip + same-loader round-trip
**Path/Symbol:** `pydantic_evals/pydantic_evals/generation.py:generate_dataset` (:33-87, whole file; module is 87L with this as its only public symbol); schema builder `dataset.py:model_json_schema_with_evaluators` (cited by eval-dataset-wire-roundtrip); load path `dataset.py:from_text` (same capsule); fence stripper `pydantic_ai_slim/pydantic_ai/_utils.py:strip_markdown_fences`.
**Signature:** `async def generate_dataset(*, dataset_type: type[Dataset[InputsT, OutputT, MetadataT]], path: Path | str | None = None, custom_evaluator_types: Sequence[type[Evaluator]] = (), model: Model | KnownModelName = 'openai:gpt-5.2', n_examples: int = 3, extra_instructions: str | None = None) -> Dataset[...]`.
**Data Shape:** prompt carries the full JSON schema of the shadow generic classes (cases with inputs/expected_output/metadata/evaluators specs); LLM returns TEXT; parsed result is a live `Dataset` holding real evaluator instances.

### Decisive source
```python
output_schema = dataset_type.model_json_schema_with_evaluators(custom_evaluator_types)

# TODO: Use `output_type=StructuredDict(output_schema)` ... once pydantic#12145 is fixed
agent = Agent(
    model,
    system_prompt=(
        f'Generate an object that is in compliance with this JSON schema:\n{output_schema}\n\n'
        f'Include {n_examples} example cases.'
        ' You must not include any characters in your response before the opening { of the JSON object, or after the closing }.'
    ),
    output_type=str,                                   # DELIBERATE str detour (see Flow)
)

default_name = Path(path).stem if path is not None else 'generated'
result = await agent.run(extra_instructions or 'Please generate the object.')
output = strip_markdown_fences(result.output)          # defense against ```json fences
try:
    result = dataset_type.from_text(                   # SAME loader as user files
        output, fmt='json', default_name=default_name, custom_evaluator_types=custom_evaluator_types
    )
except ValidationError as e:  # pragma: no cover
    print(f'Raw response from model:\n{result.output}')   # `result` still = AgentRunResult here
    raise e
if path is not None:
    result.to_file(path, custom_evaluator_types=custom_evaluator_types)  # pragma: no cover
return result
```

**Flow:** (1) build the editor-grade schema via the SAME shadow-class builder used for $schema sidecars, so generation and loading share one type truth; (2) run the agent with `output_type=str` — a pinned TODO explains why structured output is NOT used: StructuredDict's InlineDefsJsonSchemaTransformer breaks the generated schema (pydantic#12145); (3) strip markdown fences from the text because models ignore the "no characters before {" instruction; (4) parse through `from_text(fmt='json')` — registry resolution, duplicate-evaluator rejection, and ExceptionGroup triage all apply for free, so anything the generator returns is guaranteed loadable later from disk; (5) optional `to_file` reuses the same save plane ($schema sidecar). On ValidationError the RAW model text is printed (on the except path `result` still refers to the AgentRunResult, since the reassignment happens inside the try) and the error re-raises.
**Invariant:** three rules: (1) single type truth — the prompt schema and the load schema come from one builder, so a drift between "what the LLM was told" and "what the loader accepts" is impossible by construction; (2) the artifact must pass the production loader, not a lenient generator-specific parse — generation quality is bounded by loader strictness, which is the point; (3) hostile-model defenses are layered and cheap: instruction (no fences) → strip_markdown_fences (actual defense) → loader validation (last gate).
**Probe:** `tests/evals/test_dataset.py::test_import_generate_dataset` (:1702-1708): import smoke ONLY — `from pydantic_evals.generation import generate_dataset; assert generate_dataset`. Both error/save branches carry `# pragma: no cover`; behavioral coverage rides on the heavily-tested from_text/to_file round-trip plane (eval-dataset-wire-roundtrip probes, 74-test suite GREEN at pin). Honest caveat recorded: no direct behavioral test of generate_dataset exists at this pin.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "generate_dataset model_json_schema_with_evaluators strip_markdown_fences", limit: 10, fields: ["signature", "name", "file"] });
```
Live check this pass: Codebase Memory MCP was unreachable in this session (stdio env reference unavailable at transport open); anchors confirmed by direct read of generation.py WHOLE (87L) + test_dataset.py :1702-1708 at pin `a5b5fb7a` (zero drift, clean tree).

## Verdict
Adopt the same-builder-for-prompt-and-loader rule for any "LLM emits a config/data file" feature — it is the one structural choice that makes generated artifacts replayable through your normal import path. Adopt the layered fence defense (instruct, strip, validate) rather than trusting any single layer. Adapt the str-output detour to your host's structured-output limitations; if your stack can do reliable structured output against the exact load schema, prefer it and drop the strip step. Omit the raw-output print if your host has logging — keep the re-raise either way. Coverage caveat: thin direct test coverage (import smoke only; error/save branches pragma-excluded) — claims about those branches rest on source reading plus the tested from_text plane.

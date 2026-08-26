---
name: semantic-kernel-foundation
description: Use when porting Semantic Kernel's Python kernel-core machinery — the function-invocation pipeline, filter call-stack onion, corrective tool-call feedback into chat history, bounded auto-invoke loop with parallel gather and final tool-less call, streaming exception smuggling, OTel-gated invocation telemetry, decorator-time tool metadata extraction, argument coercion, copy-on-add plugin registries, the {{...}} prompt-template block engine with quote-aware lexing and positional call grammar, and the two HTML-encoding trust gates over substituted arguments and function output.
---

# Semantic Kernel: kernel-core invocation foundation

## Use this for
Use when porting or reimplementing a kernel/function-runner for LLM orchestration: plugin function
invocation with middleware-style filters, model-driven tool calls that self-heal through chat-history
feedback instead of exceptions, bounded auto-invocation loops, and invocation-span telemetry. Source
code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `references/filter-call-stack.md` — how should filters compose so first-added runs first pre-`next` and last post-`next`?
- `references/tool-call-corrective-feedback.md` — what happens when a model emits a bad tool call (wrong name, malformed JSON, missing args)?
- `references/auto-invoke-loop-bounds.md` — how is the model-driven tool loop bounded and terminated?
- `references/inner-handler-error-absorption.md` — should a crashing plugin tool raise to the caller or feed the model an error string?
- `references/streaming-exception-smuggling.md` — how do errors travel out of a streaming function without breaking the stream protocol?
- `references/invocation-telemetry-wrapper.md` — where do spans, sensitive-data gating, duration histograms, and error status attach?
- `references/kernel-function-decorator-contract.md` — should tool metadata be parsed at decoration time or lazily at registration?
- `references/optional-union-type-parsing.md` — how do `str | None`, unions, and generics become parameter metadata with correct requiredness?
- `references/reserved-parameter-injection.md` — how does a tool receive kernel/service/arguments without letting the model inject them?
- `references/argument-gathering-coercion.md` — where do JSON-shaped tool arguments become typed Python values, and what happens on missing args?
- `references/non-streaming-result-normalization.md` — what is a sync/async/generator tool return normalized into in non-streaming mode?
- `references/plugin-registry-copy-on-add.md` — how can one function live in two plugins safely, and how are fully-qualified names parsed back?
- `references/kernel-arguments-merge-operators.md` — who wins when two argument bags (with per-service settings) merge?
- `references/template-tokenizer-lexer.md` — how do `{{...}}` blocks survive quotes, escapes, and unclosed fragments without corrupting surrounding text?
- `references/code-tokenizer-grammar.md` — what makes a legal token inside `{{ }}`, and when is a function-id actually a named argument?
- `references/code-block-arity-contract.md` — which token positions may hold what in a template function call, and when do extra tokens get silently dropped?
- `references/template-function-invocation.md` — how does an in-prompt function call resolve and invoke without mutating the caller's argument bag?
- `references/argument-enrichment-type-preservation.md` — do arguments passed from a prompt to a template-invoked function keep their Python types?
- `references/trusted-arguments-encoding-gate.md` — which argument values get HTML-escaped before a template sees them, and who can opt out?
- `references/function-output-encoding-gate.md` — when is a template function's return value escaped, and why can't quick_render execute code?

## Capsule map
- **Filter onion** — `filter-call-stack`: `(id, filter)` tuples inserted at index 0, folded over the inner function; insertion order = pre-`next` order, reverse = post-`next` order.
- **Corrective feedback** — `tool-call-corrective-feedback`: four tool-call failure classes become `FunctionResultContent` messages appended to chat history so the model retries next turn; only missing-name/unresolvable-function paths never reach a filter stack.
- **Bounded auto-invoke** — `auto-invoke-loop-bounds`: `maximum_auto_invoke_attempts` rounds of `asyncio.gather` over tool calls; any `terminate=True` context returns merged results immediately; exhausted attempts fall into `for/else` doing one final call with function-choice settings reset.
- **Error absorption** — `inner-handler-error-absorption`: the inner auto-invoke handler converts tool exceptions into error-string `FunctionResult.value`; the wrapper deepcopies the result value before writing it to history.
- **Stream smuggling** — `streaming-exception-smuggling`: `METADATA_EXCEPTION_KEY="exception"` on a yielded `FunctionResult` is re-raised as chained `KernelInvokeException` by the kernel-level stream wrappers.
- **Telemetry wrapper** — `invocation-telemetry-wrapper`: pydantic `model_rebuild()` before context creation, span + sensitive-events gating for args/results, duration histogram in `finally`, `_handle_exception` records `ERROR_TYPE` then re-raises.
- **Decorator contract** — `kernel-function-decorator-contract`: six `__kernel_function_*` attrs set eagerly at decoration; streaming flag frozen from generator kind; bad annotations fail at import, not first invoke.
- **Type parsing ladder** — `optional-union-type-parsing`: only a single non-None union member unwraps (and becomes coercible); ≥2 members stay a comma-joined required string; `include_in_function_choices=False` forces optional.
- **Reserved params** — `reserved-parameter-injection`: `kernel`/`service`/`execution_settings`/`arguments` are injected from invocation context before any user-argument lookup — model data can never shadow them.
- **Argument coercion** — `argument-gathering-coercion`: coerce only single concrete types (no comma in `type_`, concrete `type_object`); missing required raises `FunctionExecutionException`; missing optionals are omitted so Python defaults apply (metadata defaults are never injected).
- **Result normalization** — `non-streaming-result-normalization`: async-gen → full list, awaitable → await, gen → list, FunctionResult passthrough with `arguments`+`used_arguments` provenance; stream_method auto-wired only for generators.
- **Plugin registry** — `plugin-registry-copy-on-add`: every insertion parses-or-copies with deepcopied metadata and rebound plugin_name; duplicates silently overwrite; FQN joins/splits on first `-` while function names may contain `-`.
- **Arguments merge** — `kernel-arguments-merge-operators`: `|` returns new KernelArguments, RHS wins values and per-service_id settings; `|=` mutates in place; settings live outside the value dict.
- **Template lexer** — `template-tokenizer-lexer`: quote-inert pair-scan for `{{`/`}}` with `\` escaping only quotes/backslash; empty blocks degrade to literal text; single var/val promoted out of CodeBlock form; inner syntax errors re-wrapped as TemplateSyntaxError.
- **Code grammar** — `code-tokenizer-grammar`: first char dispatches `$`→var, quote→value, else function-id; tokens must be space-separated or raise; a function-id chunk containing `=` is reclassified as named arg and regex-revalidated downstream.
- **Call arity** — `code-block-arity-contract`: `[function_id] [value|var|named_arg] named_arg*` validated at construction; value/var-led blocks collapse to one token and silently ignore extras; leading named arg is always an error.
- **In-prompt invocation** — `template-function-invocation`: registry lookup → shallow-copied bag → enrich → invoke, failures normalized to TemplateRenderException at the render boundary; falsy results render as "".
- **Typed enrichment** — `argument-enrichment-type-preservation`: variable-sourced args keep raw Python types via `get_value()` while prompt text uses stringifying `render()`; slot-1 non-named arg binds positionally to parameters[0].
- **Argument trust gate** — `trusted-arguments-encoding-gate`: template-level flag short-circuits; else per-variable exemption; strings HTML-escaped; fixed safe-type set passes; complex objects raise — auto-discovered variables default to encode-by-default.
- **Output trust gate** — `function-output-encoding-gate`: function output escaped unless template OR config trust flag set (all-or-nothing); static text never escaped; quick_render refuses code blocks entirely.

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question.
Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
Microsoft semantic-kernel (MIT), `main@b39d95a34435f4c1d55dd00c86120ce118d847e1`; Codebase Memory
project `semantic-kernel` (full mode, 102,306 nodes / 390,508 edges, generation 2026-08-25T20:09:20Z;
41 parse-partial files — mostly docs/diagrams plus .NET `KernelFunctionFromMethod.cs`; images/binaries
excluded by design).

## Full view (memory graph)
Revalidate `semantic-kernel` before porting: run `index_status`, `check_index_coverage`,
`search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode,
node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims.

## Boundaries
Adopt the pure contracts: filter-onion ordering, chat-history corrective feedback, bounded retry
loop shape, exception-smuggling metadata key, telemetry wrapper skeleton, quote-aware block lexing,
construction-time call-arity validation, and encode-by-default trust gates. Adapt service selection,
provider-specific settings conversion, and the escape function's target markup to your host. Omit
Azure/OpenAI connector internals, agent/process frameworks, the Jinja2/Handlebars engine family,
and the .NET/Java planes — they are separate seams.

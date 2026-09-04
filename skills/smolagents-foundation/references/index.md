<!-- Preserved from the pre-foundation-skill-v1 loader. Detail remains historical and revision-pinned. -->


# smolagents: Code-Action Agent Foundation

## Use this for
Use when building or porting a minimal code-executing agent: the ReAct run loop and its exit machine, the restricted AST Python interpreter (security ladder, import authorization, resource fences), remote executor sandboxes (E2B/Docker/Modal/Blaxel over a Jupyter wire protocol with safe serialization), tool contracts and validation gates, model adapters (completion-kwargs precedence, stop-parameter matrix, stream stitching), memory-to-prompt rendering, multi-agent composition, and Hub packaging. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `./runloop-exit-machine.md` — when does `_run_stream` stop, and what happens at max steps?
- `./runloop-code-action-spine.md` — how does model text become executed code and an observation?
- `./runloop-parallel-tool-fanout.md` — concurrent tool calls without corrupting agent state?
- `./runloop-managed-agents.md` — sub-agents as callable tools; name/shape rules.
- `./runloop-planning-cadence.md` — planning_interval gate + summary-mode replan isolation.
- `./runloop-prompt-template-contract.md` — StrictUndefined templates and per-class variables.
- `./runloop-structured-outputs-mode.md` — response_format pipeline swap and provider gates.
- `./runloop-toolcall-parse-fallback.md` — text JSON-blob scraping when providers emit no native calls.
- `./sandbox-security-ladder.md` — layered denial of imports/builtins/dunders/return-values.
- `./sandbox-import-authorization-tree.md` — wildcard/prefix import grant semantics.
- `./sandbox-final-answer-escape.md` — BaseException control signal vs generated try/except.
- `./sandbox-resource-fences.md` — op counter, loop cap, timeout, print truncation.
- `./sandbox-state-model.md` — what persists across steps; three call namespaces.
- `./sandbox-python-semantics-gaps.md` — evaluator divergences from CPython semantics.
- `./remote-final-answer-patching.md` — exception wrapper serialized across process boundary.
- `./remote-safe-serializer.md` — safe:/pickle: prefix protocol, two-sided pickle gate.
- `./remote-jupyter-wire-family.md` — kernel-gateway choreography shared by Docker/Modal/Blaxel.
- `./remote-e2b-executor.md` — result/error channel translation incl. SDK v1/v2 fork.
- `./remote-trust-boundary.md` — local "not a sandbox" line vs remote-only/local-only features.
- `./tools-contract-gates.md` — definition/serialization/call-time validation layers.
- `./tools-decorator-source-capture.md` — @tool AST source capture for self-regenerating tools.
- `./tools-mcp-ingestion.md` — MCP server → Tool adaptation and transport rules.
- `./tools-registry-deserialization.md` — AGENT/MODEL registries blocking arbitrary instantiation.
- `./tools-agent-packaging.md` — save()/push_to_hub artifact bundle + requirements discovery.
- `./default-tools-family.md` — base tool set and interchangeable web_search twins.
- `./model-completion-precedence.md` — kwargs merge ladder + REMOVE_PARAMETER sentinel.
- `./model-stop-parameter-matrix.md` — o3/o4/gpt-5/grok denylist + client-side trimming.
- `./model-message-cleaning.md` — role conversion, image encoding, consecutive-role merging.
- `./model-stream-stitching.md` — index-keyed delta reassembly rules.
- `./model-api-resilience.md` — rate-limit retry/backoff + dual truncation budgets.
- `./memory-step-rendering.md` — steps → messages projection; error coaching; plan pivot.
- `./agent-types-boundary-wrapping.md` — AgentImage/Audio raw/string duality at boundaries.
- `./monitoring-rich-safety.md` — Text-not-markup console discipline; Monitor counters.
- `./gradio-streaming-surface.md` — consuming the run generator in a chat UI.
- `./replay-diagnostics-surface.md` — print-only step replay; why every replay log is ERROR level.
- `./run-reset-memory-contract.md` — what run(reset=True/False) wipes vs keeps (state survives).
- `./memory-step-dict-serialization.md` — step `.dict()` shapes; lossy image bytes vs raw retention.
- `./chatmessage-value-plane.md` — tool-call coercion on construct, role re-typing on from_dict, raw-stripping wire JSON.
- `./agent-error-taxonomy.md` — six-class error tree, log-on-construct side effect, {type,message} dict contract.
- `./make-json-serializable-coercion.md` — local heuristic codec; JSON-looking strings promoted to containers.
- `./tool-schema-synthesis.md` — get_json_schema pipeline; docstring-required Google format, choices→enum, OpenAI envelope.
- `./type-hint-schema-vocabulary.md` — hint→type ladder without pydantic; union folding, tuple prefixItems rejections, Image/Tensor specials.
- `./tool-calltime-argument-validation.md` — two-pass arg check at execute_tool_call only; int→number widening; Tool.__call__ never validates.
- `./nullable-semantics-overload.md` — one flag = has-default + accepts-None + omittable; two acknowledged-bug skipped tests.
- `./method-checker-name-resolution.md` — ten-set allowlist machine; dead check_imports, visit_Call asymmetry, self.* blind spot.
- `./class-body-tool-rules.md` — literal-only class attrs, literal-defaulted __init__ via zip_longest alignment; serialization-gate consumers.

## Capsule map
- **Run loop** — `runloop-exit-machine`: four exits (final answer / max-steps forced answer / interrupt / generation error) with error-as-data asymmetry. `runloop-code-action-spine`: generate→stop-sequence→append-closer→parse-ladder→fix-final-answer→execute→observe. `runloop-parallel-tool-fanout`: yield-intent-first, ThreadPoolExecutor+copy_context, sorted-id memory writes. `runloop-managed-agents`: forced task:string schema, report template, three-way name uniqueness. `runloop-planning-cadence`: interval gate keyed on memory length; summary_mode isolation. `runloop-prompt-template-contract`: whole-shape template assertion + StrictUndefined. `runloop-structured-outputs-mode`: atomic flag swapping prompts/request/parse. `runloop-toolcall-parse-fallback`: brace-slice JSON scrape with positional coaching errors.
- **Local sandbox** — `sandbox-security-ladder`: allowlist resolution + return-value re-screening. `sandbox-import-authorization-tree`: prefix tree with leaf-star wildcard truth table. `sandbox-final-answer-escape`: FinalAnswerException(BaseException). `sandbox-resource-fences`: 10M ops / 1M while-iters / 30s thread timeout / 50k print cap. `sandbox-state-model`: state>static>custom precedence; assignment-proof tools. `sandbox-python-semantics-gaps`: value-returning boolops, pandas-safe chaining, comprehension scoping, fuzzy-name fallback.
- **Remote execution** — `remote-final-answer-patching`: instance class-swap with textually-baked constants. `remote-safe-serializer`: __type__ marker JSON, two-sided pickle gate, deserializer codegen. `remote-jupyter-wire-family`: token→readiness→201-create→msg_id-correlated websocket. `remote-e2b-executor`: error.name routing, main-result attribute ladder, SDK v1/v2 fork. `remote-trust-boundary`: local≠sandbox; managed-agents cliff for remotes.
- **Tools** — `tools-contract-gates`: __init_subclass__ validation, signature↔inputs bijection, sanitize-on-call. `tool-schema-synthesis`: docstring-as-descriptions + hints-as-types, mandatory per-arg docs, choices→enum, {"type":"function"} envelope; @tool requires return hint unless zero params. `type-hint-schema-vocabulary`: origin-dispatch ladder — union fold (sorted list / anyOf / nullable), tuple prefixItems with 1-elem+ellipsis rejection, dict value-only additionalProperties, Literal→enum, Tensor→audio surprise, unknown→silent object. `tool-calltime-argument-validation`: provided-args pass (unknown key, runtime-type match, any wildcard, null-if-nullable, int→number continue) + required pass (nullable⇒omittable); enforced only in execute_tool_call → AgentToolCallError. `nullable-semantics-overload`: default and None-union both write one flag read as omittable+null-ok; two skip-marked TODO tests own the fallout. `method-checker-name-resolution`: flat-scope ten-set Load allowlist fed by per-form collectors; check_imports dead, visit_Call misses typing_names, self.* unchecked. `class-body-tool-rules`: literal-only class attrs via ast.walk, name str-Constant identifier rule, zip_longest trailing default alignment, per-method fresh checker; six serialization/remote-install consumers. `tools-decorator-source-capture`: AST body slice + synthetic self signature + __source__. `tools-mcp-ingestion`: eager-connect MCPAdapt, transport defaulting, structured_output valve. `tools-registry-deserialization`: closed AGENT/MODEL registries, HfApiModel rename shim, secret scrubbing. `tools-agent-packaging`: regenerated-source bundles, block-literal prompts.yaml, AST requirements scan. `default-tools-family`: TOOL_MAPPING set, normalized "## Search Results" contract, python_interpreter exclusion for CodeAgent.
- **Models** — `model-completion-precedence`: messages→specific→kwargs→self.kwargs with REMOVE sentinel. `model-stop-parameter-matrix`: regex denylist + trim-after fallback. `model-message-cleaning`: convert→encode→merge after deepcopy. `model-stream-stitching`: name-replace vs arguments-concatenate by index. `model-api-resilience`: string-predicate retries ×3 @60s·2ⁿ+jitter; observation vs stdout truncation split.
- **Memory & UX** — `memory-step-rendering`: projection order, retry-coaching text, plan role pivot, MRO callback registry. `agent-types-boundary-wrapping`: output_type-keyed wrap, to_raw/to_string laziness. `monitoring-rich-safety`: Text-not-markup rule, honest None on partial usage. `gradio-streaming-surface`: event-typed pump, three-spelling tag cleanup.
- **Replay & value-plane** — `replay-diagnostics-surface`: observation-pure step walk at ERROR level; detailed=log_messages with exponential-growth warning. `run-reset-memory-contract`: system prompt replaced every run, reset clears steps+monitor but NOT agent.state feeding send_variables. `memory-step-dict-serialization`: fixed-key dicts, OpenAI-shaped ToolCall, `_type`-tagged raw kept, lossy `tobytes()` images. `chatmessage-value-plane`: coerce-on-construct ladder, from_dict role re-typing via str-Enum, model_dump_json drops raw. `agent-error-taxonomy`: six classes, constructor logs, classname-as-wire-type dicts. `make-json-serializable-coercion`: bracket-heuristic string promotion, str()-ed keys, `_type`+`__dict__`, repr fallback.

## Extending the foundation
Add one `./<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
smolagents (Apache-2.0), `main@30bb1161095dbae2271e6bc3cc4c219cc3897a57`; Codebase Memory project `smolagents` (root `/mnt/hdd/utopia/inspo/smolagents`, FULL mode re-indexed 2026-08-25T20:09:04Z at HEAD, 2,756n/11,037e, parse_partial only examples/open_deep_research/requirements.txt:2-2, tests/data + __pycache__ excluded by design). Passes 1+ predate the ledger and cite the now-dead project `ext-smolagents` (root `/mnt/hdd/utopia/inspo/external/smolagents`, since removed) — same pin; pass 2 (2026-08-25) re-indexed under the short name and reconciled counts to 40 refs. Work record: `inspo/smolagents-work/{state,research,verification}.md`.

## Full view (memory graph)
Revalidate `smolagents` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims.

## Boundaries
Adopt pure contracts: run-loop exit machine, security ladder ordering, prefix-tree import grants, prefix-protocol serialization, msg_id-correlated Jupyter loop, three-gate tool validation, completion-kwargs precedence, delta stitching rules. Adapt provider-specific tables (stop-parameter matrix, retry constants, type vocabularies, backend launchers, prompt YAMLs). Omit product surfaces: Hub push UX, Gradio demo app specifics, vision_web_browser example, e2b/blaxel vendor bindings beyond their wire contracts.

## Reference-file inventory

Every preserved capsule/reference file in this foundation:

- [`agent-error-taxonomy.md`](./agent-error-taxonomy.md)
- [`agent-types-boundary-wrapping.md`](./agent-types-boundary-wrapping.md)
- [`chatmessage-value-plane.md`](./chatmessage-value-plane.md)
- [`class-body-tool-rules.md`](./class-body-tool-rules.md)
- [`default-tools-family.md`](./default-tools-family.md)
- [`gradio-streaming-surface.md`](./gradio-streaming-surface.md)
- [`make-json-serializable-coercion.md`](./make-json-serializable-coercion.md)
- [`memory-step-dict-serialization.md`](./memory-step-dict-serialization.md)
- [`memory-step-rendering.md`](./memory-step-rendering.md)
- [`method-checker-name-resolution.md`](./method-checker-name-resolution.md)
- [`model-api-resilience.md`](./model-api-resilience.md)
- [`model-completion-precedence.md`](./model-completion-precedence.md)
- [`model-message-cleaning.md`](./model-message-cleaning.md)
- [`model-stop-parameter-matrix.md`](./model-stop-parameter-matrix.md)
- [`model-stream-stitching.md`](./model-stream-stitching.md)
- [`monitoring-rich-safety.md`](./monitoring-rich-safety.md)
- [`nullable-semantics-overload.md`](./nullable-semantics-overload.md)
- [`remote-e2b-executor.md`](./remote-e2b-executor.md)
- [`remote-final-answer-patching.md`](./remote-final-answer-patching.md)
- [`remote-jupyter-wire-family.md`](./remote-jupyter-wire-family.md)
- [`remote-safe-serializer.md`](./remote-safe-serializer.md)
- [`remote-trust-boundary.md`](./remote-trust-boundary.md)
- [`replay-diagnostics-surface.md`](./replay-diagnostics-surface.md)
- [`run-reset-memory-contract.md`](./run-reset-memory-contract.md)
- [`runloop-code-action-spine.md`](./runloop-code-action-spine.md)
- [`runloop-exit-machine.md`](./runloop-exit-machine.md)
- [`runloop-managed-agents.md`](./runloop-managed-agents.md)
- [`runloop-parallel-tool-fanout.md`](./runloop-parallel-tool-fanout.md)
- [`runloop-planning-cadence.md`](./runloop-planning-cadence.md)
- [`runloop-prompt-template-contract.md`](./runloop-prompt-template-contract.md)
- [`runloop-structured-outputs-mode.md`](./runloop-structured-outputs-mode.md)
- [`runloop-toolcall-parse-fallback.md`](./runloop-toolcall-parse-fallback.md)
- [`sandbox-final-answer-escape.md`](./sandbox-final-answer-escape.md)
- [`sandbox-import-authorization-tree.md`](./sandbox-import-authorization-tree.md)
- [`sandbox-python-semantics-gaps.md`](./sandbox-python-semantics-gaps.md)
- [`sandbox-resource-fences.md`](./sandbox-resource-fences.md)
- [`sandbox-security-ladder.md`](./sandbox-security-ladder.md)
- [`sandbox-state-model.md`](./sandbox-state-model.md)
- [`tool-calltime-argument-validation.md`](./tool-calltime-argument-validation.md)
- [`tool-schema-synthesis.md`](./tool-schema-synthesis.md)
- [`tools-agent-packaging.md`](./tools-agent-packaging.md)
- [`tools-contract-gates.md`](./tools-contract-gates.md)
- [`tools-decorator-source-capture.md`](./tools-decorator-source-capture.md)
- [`tools-mcp-ingestion.md`](./tools-mcp-ingestion.md)
- [`tools-registry-deserialization.md`](./tools-registry-deserialization.md)
- [`type-hint-schema-vocabulary.md`](./type-hint-schema-vocabulary.md)

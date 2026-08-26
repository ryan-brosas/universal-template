<!-- capsule-v2 -->
# Single-shot runner — how does a full turn-loop agent serve as a one-call structured function?

**Source:** pipeshub-ai Apache-2.0 `main@4a02110d`; Codebase Memory `pipeshub-ai`. **Question:** How do you reuse the whole Agent/loop machinery for auxiliary "one structured LLM call" jobs (intent parse, goal build, best-of-N judge) without hand-rolling prompts or parsers — and what exactly fails vs. what the caller must catch?

## Minimal runtime + one-terminal-tool spec + lenient parse
**Path/Symbol:** `backend/python/app/agent_loop_lib/agent/single_shot_runner.py` — `build_task_complete_runtime` (:47-64), `run_structured_single_shot` (:128-157), `parse_json_task_output` (:87-110), `run_text_single_shot`/`parse_text_task_output` (:113-125, :160-197), `StructuredSingleShotError` (:43-44).
**Signature:** `build_task_complete_runtime(transport_registry, *, opik_enabled=False, opik_project_name=None) -> AgentRuntime`; `async def run_structured_single_shot(*, name, system_prompt, goal, runtime, model_spec, output_schema_hint="", seed_messages=None, session_id=None) -> dict[str, Any]`.
**Data Shape:** A purpose-built minimal `AgentRuntime` holding ONLY a `task_complete` tool plus the caller's transport registry. The assembled `AgentSpec` pins `tool_names=["task_complete"]`, `loop=SingleShotLoop()`, `max_turns=1`. Output contract travels in the SYSTEM PROMPT: `system_prompt + output_schema_hint + _TASK_COMPLETE_SUFFIX` (the suffix demands `task_complete` be called exactly once with a JSON-string `output`, no markdown fences).

### Decisive source
```python
spec = AgentSpec(
    name=name,
    system_prompt=system_prompt + output_schema_hint + _TASK_COMPLETE_SUFFIX,
    tool_names=["task_complete"],
    model=model_spec,
    loop=SingleShotLoop(),
    max_turns=1,
)
result = await run_single_shot(spec, runtime, goal,
    seed_messages=seed_messages, skip_start=seed_messages is not None,
    session_id=session_id)
return parse_json_task_output(result)

# parse_json_task_output — fence-tolerant, object-strict:
fence_match = re.match(r"^```(?:json)?\s*(.*?)```\s*$", text, flags=re.DOTALL | re.IGNORECASE)
if fence_match:
    text = fence_match.group(1).strip()
parsed = json.loads(text)          # JSONDecodeError -> StructuredSingleShotError
if not isinstance(parsed, dict):   # arrays/scalars rejected
    raise StructuredSingleShotError("single-shot output JSON must be an object")
```

**Flow:** build the minimal runtime once per call-site → assemble spec (prompt carries the schema hint) → `run_single_shot` drives one real `Agent.run()` (seeded messages go into a fresh `ContextManager` + `skip_start`) → `parse_json_task_output` strips an optional ```json fence, `json.loads`, requires a dict → every failure mode (run failed, empty output, bad JSON, non-object) raises the ONE `StructuredSingleShotError`. The unstructured twin (`run_text_single_shot`) asserts nothing about format: the hint merely SUGGESTS layout, `parse_text_task_output` returns the string verbatim — only failed runs and genuinely empty output raise, because those callers parse leniently downstream.
**Invariant:** (1) `max_turns=1` + `SingleShotLoop` makes `task_complete` the only exit — the runner IS a function call wearing an agent. (2) Schema enforcement is prompt-side; parsing is lenient about wrapping (fences) but STRICT about shape (must be a JSON object). (3) Exactly one exception type crosses the boundary — the CALLER owns the fallback policy (IntentParser→echo raw message; GoalBuilder→raw-description goal; best-of-N judge→first successful candidate). (4) The text variant never parses — drifting from the suggested format degrades gracefully instead of raising.
**Probe:** `backend/python/tests/unit/agent_loop_lib/agent/test_task_complete_output_contract.py` (end-to-end: typed `task_complete` fields confidence/record_ids/needs_input reach `AgentResult` through the full plumbing chain); judge/intent consumers patch this module by path (`tests/unit/agent_loop_lib/agent/test_best_of_n.py:65`, `tests/unit/agents/adapter/test_intent_helpers.py:233`) pinning the seam boundary.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pipeshub-ai", query: "run_structured_single_shot build_task_complete_runtime", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the minimal-runtime-per-purpose factory, the one-terminal-tool spec with `max_turns=1`, prompt-side schema hints, and the lenient-wrap/strict-shape parse split behind one exception type; adapt the suffix wording, tool name, and schema-hint phrasing to host; omit the Opik plumbing if tracing is centralized elsewhere. No direct unit test executes the runner unparsed (consumers patch it); the output contract itself is e2e-tested.

<!-- capsule-v2 -->
# BA tool-registration grammar — how do you expose ten Playwright skills to a pydantic-ai agent, and which ONE tool earns RunContext?

**Source:** TheAgenticBrowser (TheAgentic Community License 1.0 — source-available; SaaS-competing-use restricted) `main@71daa28`; Codebase Memory `mnt-hdd-utopia-inspo-TheAgenticBrowser`. **Question:** When wrapping browser skills as LLM tools, when does a tool need agent context versus a plain delegation, and how do you keep the hand-written system prompt from drifting off the registered schema?

## The registry plane: 9 × tool_plain + exactly 1 × tool
**Path/Symbol:** `core/agents/browser_agent.py`: `current_step_class` (:26-27), `BA_client`/`BA_model` (:227-228), `BA_agent = Agent(...)` (:229-238), wrappers `google_search_tool` :243, `bulk_enter_text_tool` :250, `enter_text_tool` :259, `get_dom_text` :266, `get_dom_fields` :271, `get_url_tool` :275, `click_tool` :282, `open_url_tool` :296, `extract_text_from_pdf_tool` :303, `press_key_combination_tool` :311. Graph: `search_graph file_pattern=*browser_agent*` lists all 17 symbols.
**Signature:** `BA_agent = Agent(model=OpenAIModel(model_name=os.getenv("AGENTIC_BROWSER_TEXT_MODEL"), openai_client=BA_client), system_prompt=BA_SYS_PROMPT, deps_type=current_step_class, name="Browser Agent", retries=3, model_settings=ModelSettings(temperature=0.5))`; the lone context tool is `@BA_agent.tool async def get_dom_fields(ctx: RunContext[current_step_class]) -> str`.
**Data Shape:** Every wrapper is a one-line delegation whose docstring becomes the tool schema. `deps_type=current_step_class(BaseModel)` with field `current_step: str` is the ONLY dependency channel; `get_dom_fields` reads `ctx.deps.current_step` and forwards it to `get_dom_field_func` (whose body `print()`s it at `get_dom_with_content_type.py:87` — stray debug, don't copy).

### Decisive source
```python
# :270-272 — the ONLY @tool on the agent; everything else is @tool_plain
@BA_agent.tool
async def get_dom_fields(ctx: RunContext[current_step_class]) -> str:
    return await get_dom_field_func(ctx.deps.current_step)
```
Verified divergence (`BA_SYS_PROMPT` :50 vs registry :271): the ~195-line XML-sectioned prompt teaches `<general_rules> 8. Call the get_dom_fields tool to get the fields on the page pass a detailed prompt as to what kind of fields you are looking for.` — but the REGISTERED tool takes NO arguments beyond RunContext. The dual-maintenance drift is shipped, not hypothetical.
**Flow:** module import constructs client/model/agent once → decorators register 10 tools → loop calls `BA_agent.run(step, deps=current_step_class(...))` → pydantic-ai emits tool calls → wrappers delegate to `core/skills/*` error-as-data primitives.
**Invariant:** Tools that need loop state ride `deps_type` + `RunContext`, NOT extra prompt-visible parameters; if the prompt and schema disagree, the SCHEMA wins at runtime and the prompt silently teaches phantom usage (here: harmless-ish, but it invites the model to pass an argument the schema rejects). Keep wrapper docstrings load-bearing — they are the model-facing contract.
**Probe:** `cd $REFERENCE_ROOT/TheAgenticBrowser && grep -c "@BA_agent.tool_plain" core/agents/browser_agent.py` → `9`; `grep -c "@BA_agent.tool$" core/agents/browser_agent.py` → `1`; `grep -n "pass a detailed prompt" core/agents/browser_agent.py` → `:50`; `grep -n "ctx.deps.current_step" core/agents/browser_agent.py` → `:272`. Coverage caveat: repo ships no tests.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-TheAgenticBrowser", query: "tool_plain RunContext deps_type current_step get_dom_fields", limit: 10 });
```

## Verdict
Adopt: thin delegating wrappers with docstring-as-schema; exactly-one-context-tool discipline (state flows through `deps`, not invented parameters); retries=3 / temperature=0.5 as the action-agent baseline. Adapt: model env knob and agent name per host. Fix-at-port: reconcile the hand-written prompt against the registry mechanically (generate the tools section from signatures) so prompt-teaches-phantom-signature drift can't ship. Omit: the stray `print(raw_data)` debug in the fields path. Caveat: no upstream tests; graph coverage `no_recorded_issue` at generation `2026-08-23T00:02:33Z`.

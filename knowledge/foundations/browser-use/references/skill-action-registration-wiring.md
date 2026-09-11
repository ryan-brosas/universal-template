<!-- capsule-v2 -->
# Skill action registration — slug grammar, closure factories, and post-registration schema rebuild

**Source:** browser-use MIT `main@85ddbfedf609`; Codebase Memory `browser-use`. **Question:** how do you turn a set of remote vendor actions into first-class agent actions without late-binding bugs or stale schema unions?

## Connected graph-selected seam
**Path/Symbol:** `browser_use/agent/service.py`: XOR gate (:334-347), `Agent._get_skill_slug` (:795-828, graph-confirmed range), `_register_skills_as_actions` (:830-916), run() call site (:2575-2576).
**Signature:** `_get_skill_slug(self, skill: 'Skill', all_skills: list['Skill']) -> str`; `_register_skills_as_actions(self) -> None` (one-shot latch `_skills_registered`); handler factory `make_skill_handler(skill_id: str)` returning `async def skill_handler(params: BaseModel) -> ActionResult`.
**Data Shape:** skills → one action each; name = slug; description = `{skill.description} (Skill: "{title}")`; param model from `parameters_pydantic(exclude_cookies=True)`.

### Decisive source
```python
# :806-828 — slug grammar + collision suffix keyed to the skill's OWN id prefix
slug = re.sub(r'[^\w\s]', '', skill.title.lower())
slug = re.sub(r'[\s\-]+', '_', slug).strip('_')
same_slug_count = sum(1 for s in all_skills if ... == slug)
if same_slug_count > 1:
    return f'{slug}_{skill.id[:4]}'

# :852-856 — closure FACTORY binds skill_id now (late-binding bug avoided)
def make_skill_handler(skill_id: str):
    async def skill_handler(params: BaseModel) -> ActionResult:
        ...
# :903-914 — the ActionModel union CHANGED, so rebuild + round-trip reconvert initial actions
self._setup_action_models()
if self.initial_actions:
    initial_actions_dict = [a.model_dump(exclude_unset=True) for a in self.initial_actions]
    self.initial_actions = self._convert_initial_actions(initial_actions_dict)
```

**Flow:** constructor enforces `skills` XOR `skill_ids` (ValueError; `skills` takes precedence; an injected `skill_service` wins over both) -> `run()` calls registration ONCE after `browser_session.start()` (:2575-2576) -> per skill: slug, param model, description, factory-made handler registered via `registry.action(...)` -> latch set -> `_setup_action_models()` rebuilds the per-page discriminated union -> existing `initial_actions` are dumped (`exclude_unset`) and reconverted under the NEW ActionModel type.
**Invariant:** handlers fetch live cookies PER CALL (:867) — never cache credentials at registration time; outcome mapping is success→`ActionResult(extracted_content=str(result.result))`, `result.success False`→`error=result.error`, any exception→`error=f'Skill execution error: {type}: {e}'`; the MissingCookieException branch renders guided remediation text (see skill-cookie-param-injection). BETA ASYMMETRY: beta/service.py accepts skill_service/skill_ids but never registers or executes skills (inert param at this pin). Slug collisions are deterministic: probe showed dup titles "Get Weather Data"×2 → `get_weather_data_aaaa`/`get_weather_data_bbbb` (own id[:4]), unique title unsuffixed.
**Probe:** `.venv/bin/python -c` from repo root: call `Agent._get_skill_slug` unbound over two same-titled Skills with distinct UUIDs and one unique-titled Skill; expect id[:4]-suffixed slugs for the dups only (executed this pass; outputs in verification.md).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-use", query: "_get_skill_slug register skills as actions", limit: 10 });
```
Executed during discovery: rank-3 hit `Agent._get_skill_slug` :795-828.

## Verdict
Adopt the pattern wholesale for ANY dynamic action source (plugins, MCP, macros): dedupe names via content-derived slug + stable id-prefix suffix, bind loop variables through a factory, keep credential fetch inside the handler, and ALWAYS rebuild/reconvert your action-schema unions after mutating the registry. Adapt slug charset to your host's action-name grammar. Omit browser-use's registry specifics (action-registry capsule owns that contract).

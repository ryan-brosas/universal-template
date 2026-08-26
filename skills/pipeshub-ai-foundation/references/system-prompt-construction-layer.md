<!-- capsule-v2 -->
# System prompt construction layer — how does a per-turn prompt stay fresh without the spec (or the caller) rebuilding anything?

**Source:** pipeshub-ai Apache-2.0 `main@4a02110dd9a7a644d8ba7a5ccd295c58a3c3628f`; Codebase Memory `pipeshub-ai`. **Question:** How do identity, toolsets, skills, todos, and mode compose into one system prompt each turn — and how does a caller swap the whole assembly strategy?

## AgentSpec holds; builder builds: named-section template rendered FRESH every turn with override-by-name semantics
**Path/Symbol:** `backend/python/app/agent_loop_lib/agent/prompt.py:SystemPromptBuilder/DefaultPromptBuilder/build_system_prompt/render_skills_overview` (L24–206); Layer-0 holder `agent/spec.py:AgentSpec` (L52–108: `system_prompt: str | SystemPromptBuilder`, `extra_prompt_sections`, `prompt_section_order`); section store `roles/prompt_template.py:PromptTemplate/MODE_GUIDANCE`.
**Signature:** `build(spec, runtime, goal, todos, extra_sections: dict[str,str]) -> str`; `build_system_prompt(spec, runtime, goal, todos=None, extra_sections=None) -> str` dispatches on `isinstance(spec.system_prompt, str)`.
**Data Shape:** Named sections (`identity/goal_brief/toolset_overview/skills_overview/todos/mode/style`) set into a PromptTemplate then rendered in `spec.prompt_section_order`; run-scoped `extra_sections` overlay spec-level ones by name.

### Decisive source
```python
@runtime_checkable
class SystemPromptBuilder(Protocol):
    """Assembles the per-turn system prompt. Called fresh every turn (cheap:
    string assembly, no I/O) so sections that change over the run — mode,
    toolset overview, todos — stay accurate without the caller rebuilding
    anything else."""

# DefaultPromptBuilder.build — spec sections first, RUN overrides win:
for name, content in spec.extra_prompt_sections.items():
    template.set(name, content)
for name, content in extra_sections.items():
    template.set(name, content)      # set() overwrites by name — even "mode"
return template.render(spec.prompt_section_order)
```

**Flow:** each turn the loop calls build_system_prompt → plain-string prompts take DefaultPromptBuilder; object prompts delegate to the injected builder → sections render: identity, goal brief, toolset overview tree (from `registry.toolset_overview()`, recursing children), skills overview, todo list with `[ ]/[~]/[x]` markers, mode guidance, optional output style → overlays applied last-wins.
**Invariant:** (1) Construction is Layer 1, deliberately separate from Layer 0 (`AgentSpec` merely HOLDS) — swapping to CMS-loaded or A/B-tested assembly touches nothing downstream. (2) build() must stay pure string assembly with NO I/O every turn — that's what makes fresh-per-turn safe; skill/toolset reads come from in-memory sync snapshots (`catalog_snapshot()`). (3) Skills overview is level-1 disclosure ONLY (name + first-sentence-capped description; category tree above `catalog_render_limit`) plus an explicit do-NOT-load-upfront instruction. (4) Public `render_skills_overview` lets host builders (PipesHubPromptBuilder) render the identical section instead of forking it.
**Probe:** No direct unit test targets `agent_loop_lib/agent/prompt.py` at HEAD — caveat recorded. Indirect pins: `tests/unit/agents/adapter/test_prompt_invariants.py` (golden snapshots + per-invariant assertions over assembled prompts at the integration layer); AgentSpec consumers exercised across `tests/unit/agent_loop_lib/agent/test_*.py`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pipeshub-ai", query: "SystemPromptBuilder DefaultPromptBuilder build_system_prompt render_skills_overview", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the hold-vs-build split + fresh-cheap-pure build contract + named-section override order (spec < run). Adapt section vocabulary to host needs. Omit the specific section copy (host voice). Coverage caveat: library-layer builder itself untested upstream; integration-layer golden tests pin observable output.

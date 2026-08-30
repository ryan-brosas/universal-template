<!-- capsule-v2 -->
# Progressive disclosure & preloading — how do 3 tiers plus a deterministic PRE_AGENT preload keep a big catalog off the prompt budget?

**Source:** pipeshub-ai (Apache-2.0) `main@4a02110dd9a7a644d8ba7a5ccd295c58a3c3628f`; Codebase Memory `pipeshub-ai`. **Question:** A porter scaling skills past a handful must know the three disclosure tiers, the relevance-band rules for auto-preloading, and why a pointer is WORSE than nothing for an agent that can't follow it.

## Three-tier progressive disclosure
**Path/Symbol:** `manager.py:SkillManager.catalog_snapshot` (tier 1, sync), `activate_skill` (138-146, tier 2), `load_resource` (148-153, tier 3); resource enumeration `loader.py:discover_resources` (87-103).
**Signature:** tier1 `catalog_snapshot() -> list[SkillMetadata]`; tier2 `async activate_skill(name, session_id=None) -> Skill`; tier3 `async load_resource(name, path) -> str`.
**Data Shape:** Tier 1 = name+description only (~100 words/skill, always in context). Tier 2 = full body on demand via load_skill tool; records activation when session given. Tier 3 = bundled scripts/references/assets read via filesystem tools, never preloaded.

### Decisive source
```python
# base.py — level-3 listing is precomputed but contents NEVER eagerly read
resources: dict[str, list[str]] = Field(default_factory=dict)
# "the agent decides which, if any, to load via load_skill_resource;
#  this module never reads their contents eagerly"
```

**Flow:** every turn renders tier-1 overview → model calls `load_skill(name)` for the one relevant skill → reads bundled files only as needed. DEPRECATED excluded from tier 1 but still loadable by exact name (graceful in-flight-reference degradation).

## skill_preloading — relevance-band injection before turn 1
**Path/Symbol:** `hooks/middleware/builtin/skill_preloading.py:skill_preloading` factory (47-93); band renderer `_render_preload_section` (111-150); capability gate `_can_load_skills_on_demand` (96-108).
**Signature:** `skill_preloading(manager, *, preload_body_threshold=0.75, mention_threshold=0.4, top_k=5)` → PRE_AGENT middleware writing `ctx.scope.extra_prompt_sections["preloaded_skills"]`.
**Data Shape:** Search goal description against catalog (top_k=5) → three bands: ≥0.75 full body injected (+activation recorded); 0.4–0.75 pointer line only; <0.4 nothing.

### Decisive source
```python
# skill_preloading.py — the pointer-suppression gate IS the capsule
elif emit_pointers and match.relevance >= mention_threshold:
    pointers.append(f"- {match.skill.name}: {match.skill.description}")

def _can_load_skills_on_demand(scope) -> bool:
    tool_names = scope.spec.tool_names
    if tool_names is None: return True          # no allowlist ⇒ has everything incl. load_skill
    return "load_skill" in tool_names           # explicit allowlist without it ⇒ can't act
```

**Flow:** PRE_AGENT → search goal vs catalog → for each match by band: activate+inject body, or emit pointer, or skip → write/clear the prompt section → next_fn. Activation failure degrades to pointer WHEN the agent could act on it.
**Invariant:** Defaults favor precision over recall — a wrong full-body injection wastes context EVERY turn, not once. The mention band collapses to NOTHING when the about-to-run agent lacks `load_skill` in its own tool_names (scoped domain children): injecting an instruction the model structurally cannot obey is worse than injecting nothing. Body band is unaffected by that gate (needs no follow-up call). No-op guards never raise — preloading finding nothing is normal.
**Probe:** `tests/unit/agent_loop_lib/hooks/middleware/builtin/test_skill_preloading.py::TestRelevanceBands` (pins all three bands + activation-failure→pointer fallback), `TestScopedAgentWithoutLoadSkill` (pins pointer suppression, body survival, silent drop on failure without load_skill, pointer restored when allowlist includes load_skill), `TestNoOpGuards`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pipeshub-ai", query: "skill_preloading _render_preload_section", limit: 10 });
await mcp.codebase_memory.search_graph({ project: "pipeshub-ai", query: "activate_skill load_resource", limit: 10 });
```

## Verdict
Adopt the three-tier ladder (metadata always / body on demand / resources enumerated-not-read), the two-threshold preload bands with precision-favoring defaults, and the actability gate that suppresses pointers for agents lacking load_skill. Adapt thresholds per deployment and the section key/rendering to your prompt builder. Omit nothing — this seam is small and entirely portable. Direct tests confirm all invariants; index coverage clean.

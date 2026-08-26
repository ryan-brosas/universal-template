<!-- capsule-v2 -->
# Pluggable shortlister strategy seam — how do you make an LLM tool-ranker swappable by config without changing the default path byte-for-byte?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f` (feature #624/#664); Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** You have a fused LLM ranking step called from two sites and want third parties to swap in a cosine/dotted-path ranker — where does the seam live so the default behavior is untouched at every catalogue size?

## Strategy protocol + typed plan + factory
**Path/Symbol:** `src/cuga/backend/cuga_graph/nodes/cuga_lite/shortlister/base.py:19-91` (`ShortlistCandidate`, `ShortlistRequest`, `ShortlistResult`, `ShortlisterUnavailableError`, `ShortlisterStrategy` Protocol); `plan.py:50-92` (`ShortlisterPlan`, `cache_key`), `:133-182` (`ShortlisterRouter.resolve`); `factory.py:90-147` (`resolve_shortlister`, `run_shortlister`).
**Signature:** `async shortlist(self, request: ShortlistRequest) -> ShortlistResult`; `ShortlisterRouter.resolve(settings, *, seam="discovery", configurable=None, override=None) -> ShortlisterPlan`.
**Data Shape:** `ShortlistCandidate{name, score, reasoning=""}` — score is strategy-defined and never compared across strategies. `top_k=None` means "strategy decides count" (find_tools semantic). `ShortlistResult.notes` carries strategy annotations (filtered-names footer) to the renderer.

### Decisive source
```python
# factory.py:126-147 — ONLY unavailability degrades; genuine failures propagate
async def run_shortlister(plan, request):
    strategy = resolve_shortlister(plan)
    try:
        return await strategy.shortlist(request)
    except ShortlisterUnavailableError as e:
        fallback_name = plan.fallback_strategy
        if fallback_name == plan.strategy or fallback_name not in _BUILDERS:
            raise
        logger.warning("Shortlister {!r} unavailable ({}); using {!r} for this call.",
                       plan.strategy, e, fallback_name)
        return await _BUILDERS[fallback_name](plan).shortlist(request)
```
```python
# plan.py:163-181 — resolve() post-validation; note the pydantic-copy trap
plan = ShortlisterPlan(seam=seam, instance=instance, notes=notes, **values)
# Append to ``plan.notes``, not the local list — pydantic copies it on
# validation, so mutating ``notes`` here would silently do nothing.
if plan.instance is None and plan.strategy not in BUILTIN_STRATEGIES and "." not in plan.strategy:
    plan.notes.append(f"unknown shortlister strategy {plan.strategy!r}; falling back ...")
    plan.strategy = DEFAULT_STRATEGY          # unknown bare name → llm + visible note
if plan.top_k < 0: plan.top_k = 0
if plan.max_results <= 0: plan.max_results = DEFAULT_MAX_RESULTS
plan.query_weight = min(max(plan.query_weight, 0.0), 1.0)   # clamp, never fail
plan.min_score   = min(max(plan.min_score, -1.0), 1.0)
```

**Flow:** precedence layers highest-first: `override` (SDK dataclass or live instance) → `configurable["shortlister_*"]` per-invoke → `[shortlister.<seam>]` per-seam TOML → `[shortlister]` global TOML → module defaults in `plan.py:26-34` (NOT settings.toml — "a missing section can never break resolution"). `_layer()` copies only recognized non-None values after `_coerce()` (env vars arrive as strings; a garbage value is DROPPED to the lower source, never raises — one typo must not take the agent down). Factory caches instances by `plan.cache_key()` = strategy|fallback|provider|model|qw|ms — constructor-affecting fields only: `top_k`/`max_results` deliberately absent because they travel per request; including them would fragment the cache and reload model weights per call. Dotted-path strategies are loaded via `cuga.config.get_class`, and the `plan=` kwarg is decided by INSPECTING the signature (`factory.py:65-87`) — never try/except TypeError, which would misread a TypeError raised inside a real constructor.

**Invariant:** (1) The seam changes NOTHING on the default path: callers gate engagement with `engage_cosine = not plan.is_llm_only and len(all_tools) > plan.threshold` and rewrite a non-engaged plan via `plan.model_copy(update={"strategy": "llm", "instance": None})` — keying only on catalogue size would cap the default LLM path above threshold, which #624 forbids. (2) `ShortlisterUnavailableError` means "cannot run right now" (model loading, deps missing) → degrade once to `fallback_strategy`; a merely-bad ranker must NOT raise it, and ordinary exceptions propagate so each call site keeps its own error contract. (3) Unknown strategy names are rewritten at RESOLVE time with a visible note appended — the factory's ValueError only covers hand-built plans constructed directly in code. (4) `threshold`(128) ≠ `advanced_features.shortlisting_tool_threshold`(35): the former engages cosine inside the shortlister, the latter hides tools behind find_tools in the prompt.

**Probe:** direct tests `src/cuga/backend/cuga_graph/nodes/cuga_lite/tests/test_shortlister_factory.py::test_configurable_beats_settings` (:103), `::test_per_seam_section_beats_global` (:112), `::test_instances_are_cached_so_the_model_loads_once` (:155), `::test_per_call_knobs_do_not_fragment_the_cache` (:167), `::test_constructor_fields_do_fragment_the_cache` (:174), `::test_unavailable_strategy_degrades_to_fallback` (:199), `::test_ordinary_errors_are_not_swallowed` (:224); `tests/unit/test_shortlister_config_surfaces.py::test_validators_cover_every_plan_field` (:31) pins every plan field to a config Validator.

## Get live surrounding code
**Retrieve:**
```ts
mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "ShortlisterRouter resolve_shortlister ShortlisterUnavailableError", limit: 10, fields: ["signature", "name", "file"] });
```

**Verdict:** ADOPT as-is when adding a config-swappable ranker/selector behind an existing fused LLM call; the engage-gate + cache-key split (constructor vs per-request fields) is what keeps default deployments bit-identical.

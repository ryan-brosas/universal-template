<!-- capsule-v2 -->
# Conduct orchestration & image pre-generation — which branches does conduct_research take, and why are images planned BEFORE report writing?

**Source:** gpt-researcher Apache-2.0 `main@5d84d2f5553e70a2765a8ff3a0d2672d60437ce8`; Codebase Memory `gpt-researcher`. **Question:** Where must a porter hook orchestration steps so cost attribution, deep-research routing, and image embedding all keep working?

## GPTResearcher.conduct_research branch ladder
**Path/Symbol:** `gpt_researcher/agent.py:331-401` (`conduct_research`), `:403-449` (`_handle_deep_research`), `:469-486` (write_report image passthrough), `:773-794` (`add_costs` + un-awaited log quirk).
**Signature:** `async def conduct_research(self, on_progress=None)`; `_current_step: str` transitions `"general"→"deep_research"|"agent_selection"|"research"|"report_writing"`.
**Data Shape:** Returns accumulated context; sets `self.agent/self.role` as side effects when selection runs; `self.available_images: list` populated pre-report.

### Decisive source
```python
# agent.py:350-353 — deep research needs BOTH conditions:
if self.report_type == ReportType.DeepResearch.value and self.deep_researcher:
    self._current_step = "deep_research"
    return await self._handle_deep_research(on_progress)
...
# agent.py:386-396 — images are planned from the finished context, before writing:
# Pre-generate images if enabled (happens BEFORE report writing for better UX)
if self.image_generator and self.image_generator.is_enabled():
    context_str = "\n\n".join(self.context) if isinstance(self.context, list) else str(self.context)
    self.available_images = await self.image_generator.plan_and_generate_images(
        context=context_str, query=self.query,
        research_id=self._generate_research_id())
```
```python
# agent.py:789-791 — sync method fires an async logger WITHOUT await:
def add_costs(self, cost: float) -> None:
    ...
    if self.log_handler:
        self._log_event("research", step="cost_update", details={...})  # never awaited
```

**Flow:** log start → deep-research gate (report_type AND constructed `deep_researcher`) → agent selection only when `agent`/`role` are both missing (the conductor repeats this defensively at researcher.py:129-137 — same guard, second call is a no-op after the first) → `research_conductor.conduct_research()` stores into `self.context` → optional image planning over the joined context string → return context; `write_report` later forwards `available_images` into `report_generator.write_report`.
**Invariant:** every LLM cost lands through `add_costs`, attributed to whichever `_current_step` was last set — reordering steps silently mis-buckets spend. The un-awaited `_log_event` inside sync `add_costs` creates a coroutine that NEVER runs (RuntimeWarning under `-W error::RuntimeWarning`); a porter must either make it fire-and-log via `asyncio.create_task` guarded by a loop check or drop it — do not "fix" by adding await without making the method async. Research-id is lazily memoized md5(query+time)[:12] prefixed `research_`.
**Probe:** runner BLOCKED in-lane (missing aiofiles/deps; read-only checkout). Deterministic anchors verified byte-exact: `ReportType.DeepResearch.value and self.deep_researcher` :351, `BEFORE report writing` comment :386, bare `self._log_event("research", step="cost_update"` :790 (no await prefix). Direct tests absent upstream for the branch ladder itself; tests/report-types.py exercises it end-to-end only with live API keys.
**Coverage:** check_index_coverage `no_recorded_issue`/`metadata_match` for agent.py @ gen 2026-08-26T01:42:19Z.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "gpt-researcher", query: "conduct_research available_images plan_and_generate_images", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the branch order, the double-condition deep-research gate, and step-keyed cost attribution; treat image pre-generation as an ordering contract (context-complete, write-pending), not a detail. Adapt the image generator and event sink to your host. Omit ModelsLab-specific provider checks; keep or consciously remove the un-awaited-log quirk rather than inheriting it silently.

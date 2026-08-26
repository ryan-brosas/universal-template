<!-- capsule-v2 -->
# Skill usage tracking & outcome feedback — how does the loop close on whether an existing skill actually helped?

**Source:** pipeshub-ai (Apache-2.0) `main@4a02110dd9a7a644d8ba7a5ccd295c58a3c3628f`; Codebase Memory `pipeshub-ai`. **Question:** A porter wiring skill learning must know who records activations/outcomes when, and how accumulated experience converts into keep/refine/deprecate decisions.

## SkillLearning POST_AGENT middleware — outcome feedback + extraction trigger
**Path/Symbol:** `hooks/middleware/builtin/skill_learning.py:SkillLearning.__call__` (84-94), `_record_outcomes` (96-104), `_learn` (106-133); `_skill_names_loaded` (47-53); `_writer_goal` (56-68).
**Signature:** `SkillLearning(manager, spawn_skill_writer, timeline_store=None)`; `async __call__(ctx: AgentLifecycleContext, next_fn)`.
**Data Shape:** Loaded-skill set = names from every `load_skill` tool call's `arguments["name"]` in the run. Writer goal string embeds candidate name/description/body + trajectory summary + an instruction to call `skill_manage(action='create', ...)` EXACTLY once.

### Decisive source
```python
# skill_learning.py — feedback for OLD skills, extraction only on SUCCESS
await self._record_outcomes(result, ctx.session_id)   # always, even failed runs
if result.success:
    await self._learn(ctx, result)                     # extraction gate

for candidate in candidates:
    if candidate.status != "approved":
        continue        # pending ones were already queued by the manager
    await self._spawn(_writer_goal(candidate))         # sub-agent authors + persists via skill_manage
```

**Flow:** run finishes → for each load_skill'd skill record activation+outcome against tracker (per-run exceptions logged, never fatal) → if success: build trajectory+decision_trace from timeline (tolerant of missing store) → manager.learn_from_execution → spawn writer sub-agent per approved candidate.
**Invariant:** Outcome feedback runs on FAILED runs too — that's where underperforming skills get their failure data; extraction runs ONLY on success (don't distill skills from failures). The middleware NEVER persists a skill itself ("everything via tool calls" — persistence rides the writer sub-agent's skill_manage call). Every stage is exception-guarded so learning can never break the run that produced it.
**Probe:** `tests/unit/agent_loop_lib/hooks/middleware/builtin/test_skill_learning.py` (FakeSkillManager pins learn_from_execution contract, outcome recording, writer-spawn-on-approved-only).

## SkillUsageTracker ABC + InMemoryUsageTracker
**Path/Symbol:** `modules/providers/skills/tracker.py` ABC (14-39); `in_memory_tracker.py:InMemoryUsageTracker` (9-56); experience model `base.py:SkillExperience` (192-209) with `success_rate = 1.0` when zero outcomes.
**Signature:** `record_activation(skill_name, session_id)` / `record_outcome(skill_name, session_id, success, notes="")` / `get_experience(skill_name)` / `get_underperforming(threshold=0.5)` / `get_unused(since_days=30)`.
**Data Shape:** One SkillExperience per name: total_activations, successful/failed_outcomes, last_activated ISO ts, failure_modes[], improvement_notes[].
**Invariant:** Unknown skill ⇒ fresh all-zero experience, NEVER a raise ("no experience yet" is normal). Zero-outcome success_rate defaults to 1.0 (healthy) — new skills can't be flagged before evidence. Tracker kept separate from SkillStore so content storage never learns about activations.
**Probe:** exercised through test_manager.py FakeTracker + TestUsageTracking (:831).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pipeshub-ai", query: "SkillLearning _record_outcomes _writer_goal", limit: 10 });
await mcp.codebase_memory.search_graph({ project: "pipeshub-ai", query: "InMemoryUsageTracker get_underperforming", limit: 10 });
```

## Verdict
Adopt outcome-feedback-on-all-runs + extraction-only-on-success split, the writer-sub-agent persistence handoff with exactly-one-tool-call goal framing, all-or-nothing exception guarding around learning, and the zero-experience-is-healthy default. Adapt the writer-goal prompt and failure-mode note capture to host conventions. Omit the retired `skill_creation.py` middleware it replaced.

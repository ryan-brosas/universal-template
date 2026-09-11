<!-- capsule-v2 -->
# ContextVar input staging for sandbox handoff — how do you pass files into a child agent's fresh sandboxes without threading parameters through every async layer?

**Source:** pipeshub-ai Apache-2.0 `main@4a02110dd9a7a644d8ba7a5ccd295c58a3c3628f`; Codebase Memory `pipeshub-ai`. **Question:** What is the correct staging primitive (ContextVar vs StateSlot), lifetime, and merge semantics when a parent's tool results and skill resources must appear inside every FRESH coding sandbox a child creates?

## Two sibling ContextVars with deliberately different lifetimes
**Path/Symbol:** `backend/python/app/agent_loop_lib/tools/builtin/sandbox/input_staging.py:stage_input_files/set_staged_input_files_for_task/peek_staged_input_files/add_staged_skill_resources/peek_staged_skill_resources/PARENT_RESULTS_INPUT_PATH` (L54–176); consumers `sandbox/coding_sandbox.py:246–247` (`peek_staged_input_files` + `peek_staged_skill_resources` at fresh-sandbox creation), producers `coordination/agent_tool.py` (`with stage_input_files(...)` around the single `run_child`) and `agents/adapter/sandbox_bridge.py` (`set_staged_input_files_for_task` from PRE middleware).
**Signature:** `stage_input_files(files: dict[str, bytes] | None)` — contextmanager yielding None; `set_staged_input_files_from_task(files)` is a bare `.set()`; both merge `{**(current or {}), **files}`; `add_staged_skill_resources(files: dict[str, bytes])` additive-only; peeks return `dict | None`.
**Data Shape:** Values are `dict[sandbox-relative path → bytes]`; canonical staged path constant `PARENT_RESULTS_INPUT_PATH = "input/parent_tool_results.json"` lives HERE so coordination and tool layers can't drift.

### Decisive source
```python
# WHY a ContextVar and not a RunScope StateSlot (module docstring): the
# consumer runs several async-call layers below AgentTool.handle(), inside
# the CHILD's own Agent.run()/step() which has no reference back to the
# parent's RunScope. contextvars propagate because everything happens on
# one asyncio.Task tree spawned from `await run_child(...)`: a plain await
# never creates a new task, and gather/create_task copy CURRENT context at
# task-creation time — still inside this module's `with` block.
if not files:
    yield / return          # falsy = no-op, no token set
merged = {**(_staged.get() or {}), **files}
token = _staged.set(merged); try: yield finally: reset(token)

# The PRE_TOOL_USE bug set_staged_input_files_for_task exists to fix:
# ToolExecutor.call_tool() runs the ENTIRE PRE pipeline to completion
# (next_fn() advances to the NEXT MIDDLEWARE, never into tool.execute()),
# THEN calls execute() — by then `with stage_input_files(): await next_fn()`
# has already unwound and reset. Bare .set() survives; safe only because
# PRE dispatch and execute() run sequentially on ONE task, while each tool
# call gets its OWN task via the turn loop's asyncio.gather, so a set never
# leaks into siblings/later calls.
```

**Flow:** `AgentTool.handle()` (share_parent_results=True) enters `with stage_input_files({PARENT_RESULTS_INPUT_PATH: payload})` around its single `run_child` → child turn loop dispatches each tool call on its own gather-spawned task (context copied at creation ⇒ still inside span) → `CodingSandboxTool.execute()` at FRESH-sandbox creation peeks both vars and uploads whatever is staged; reused sandboxes (explicit `sandbox_id`) skipped — already populated → skill scripts ride the SECOND var via `load_skill`'s `add_staged_skill_resources`, surviving the rest of the run because their lifetime requirement (any later turn's `run_code`) differs from the single-handoff span. Nested spans MERGE (spawn_scheduler stages prerequisite artifacts `input/artifacts/<task_id>/…` around the whole dependent child; inside that span AgentTool stages parent results for a grandchild); collision ⇒ inner wins; exit restores outer exactly.
**Invariant:** (1) Falsy input = true no-op that doesn't even set an empty dict — an always-on call site must never turn a clean `None` baseline into `{}` nor disturb an enclosing block. (2) Merge-don't-replace on nesting; replacing would silently vanish the outer artifact files the goal text tells the grandchild to read. (3) Deliberately NO consume-once semantics: a `.set()` inside a gather-spawned task is local to that task's copied context and never propagates back, so clearing after first upload cannot stop a later fresh sandbox from re-seeing the files; idempotent re-upload of a small JSON beats incorrect consume-once across task boundaries. (4) `set_staged_input_files_for_task` is safe ONLY under sequential-PRE-then-execute-on-one-task + per-call-task isolation; porting it into a host where PRE hooks run concurrently with execution reintroduces the leak the test pins as invisible-to-sibling-tasks. (5) Skill resources use a SEPARATE var with additive semantics and NO reset — loading skill #2 must not clobber skill #1, and there is no enclosing `with` whose exit could clear them.
**Probe:** `tests/unit/agent_loop_lib/tools/builtin/sandbox/test_input_staging.py` (dedicated 237L suite, all green upstream): nesting+restore :62–75, collision-inner-wins :77–83, survives-await-same-task :85–94, NOT-visible-in-task-created-before-staging :96–111, PRE-pipeline-survival regression class :114–204 (`test_value_survives_past_where_a_with_block_would_have_reset_it` :131–144 pins the exact bug), merges-with-enclosing-block :168–178, sibling-task isolation :186–204, skill-resources independence :207–237.
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph --project pipeshub-ai --query "stage_input_files set_staged_input_files_for_task peek_staged_skill_resources" --detail ids
```

## Verdict
Adopt the two-var split (span-scoped handoff vs run-long skill resources), merge-with-inner-wins nesting, falsy-no-op discipline, and the bare-set-for-PRE-middleware workaround WITH its documented task-model preconditions; keep `PARENT_RESULTS_INPUT_PATH` as a shared constant next to the peek API. Adapt path conventions (`input/...`) and upload mechanics to the host sandbox. Omit nothing portable. Coverage: direct dedicated test file exists (rare for this repo) — no caveat beyond read-only-runner block recorded in work record [DONE:162].

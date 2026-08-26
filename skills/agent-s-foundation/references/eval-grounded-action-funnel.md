<!-- capsule-v2 -->
# eval-grounded-action-funnel — How does a plan string become an executable grounded action, and what happens on failure?

**Source:** Agent-S MIT `main@bffdb59c`; Codebase Memory `ext-agent-s`. **Question:** How is the model's fenced code turned into a runnable action string, and why is the failure path a wait?

## Eval funnel seam
**Path/Symbol:** `gui_agents/s3/utils/common_utils.py:create_pyautogui_code` (:15-32); `gui_agents/s3/utils/common_utils.py:parse_code_from_string` (:143-166); `gui_agents/s3/agents/worker.py:generate_next_action` (:324-336).
**Signature:** `create_pyautogui_code(agent, code: str, obs) -> str` (raises on any failure); `parse_code_from_string(input_string) -> str` (last fenced block, else `""`).
**Data Shape:** Input = assistant plan text containing ONE ```python block holding a single `agent.<action>(...)` call. Output = a self-contained Python action string (`import pyautogui; pyautogui.click(x, y, ...)`), or sentinel strings `"DONE"`/`"FAIL"`/`"WAIT"` from terminal actions.

### Decisive source
```python
# worker.py — the funnel and its fallback
plan_code = parse_code_from_string(plan)
try:
    assert plan_code, "Plan code should not be empty"
    exec_code = create_pyautogui_code(self.grounding_agent, plan_code, obs)
except Exception as e:
    logger.error(f"Could not evaluate the following plan code:\n{plan_code}\nError: {e}")
    exec_code = self.grounding_agent.wait(1.333)  # Skip a turn

# common_utils.py — the last-fence-wins rule
matches = re.findall(r"```(?:\w+\s+)?(.*?)```", input_string, re.DOTALL)
if len(matches) == 0:
    return ""
relevant_code = matches[-1]  # the grounded action is the LAST match
```

**Flow:** plan text → regex extracts LAST fenced block → `eval(code)` runs with the ACI instance bound as `agent` and `obs` in scope → the called ACI method grounds coordinates against the screenshot and RETURNS a python action string → that string becomes `exec_code`, returned to the harness which `exec()`s it. Any exception (empty code, bad name, bad args, grounding assert) collapses to `agent.wait(1.333)` so the loop never dies mid-episode.
**Invariant:** (1) The ACI methods are never executed inside the agent process — `eval` only CALLS them to synthesize strings; side effects happen when the harness executes the returned string elsewhere. (2) Last-match-wins assumes one action per turn; multi-block plans silently execute only the final block. (3) Failure degrades to a timed no-op turn (1.333s), preserving trajectory continuity for reflection. (4) `assign_screenshot(obs)` must be called before grounding (create_pyautogui_code :30 does it defensively).
**Probe:** `grep -n 'exec_code = eval' gui_agents/s3/utils/common_utils.py` → :31.
**Probe:** `grep -c 'relevant_code = matches\[' gui_agents/s3/utils/common_utils.py` → 1.
**Probe:** `grep -n 'self.grounding_agent.wait' gui_agents/s3/agents/worker.py` → :333 (the skip-a-turn fallback).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-agent-s", query: "create_pyautogui_code parse_code_from_string", limit: 5 });
```

## Verdict
Adopt eval-based grounded-action synthesis with a wait-on-failure fallback — it gives typed-ish action checking (NameError/TypeError surface at plan time, before any GUI effect) without a tool-call protocol; adapt fence grammar and the wait duration; omit the OSWorld harness coupling.

<!-- capsule-v2 -->
# code-agent-handoff-contract — How does a GUI worker delegate to a code agent and read results back?

**Source:** Agent-S MIT `main@bffdb59c`; Codebase Memory `ext-agent-s`. **Question:** What is the message contract between the worker loop and the embedded code agent, and how is exactly-once consumption enforced?

## Handoff seam
**Path/Symbol:** `gui_agents/s3/agents/grounding.py:OSWorldACI.call_code_agent` (:542-603) + `last_code_agent_result` init (:227); consumption at `gui_agents/s3/agents/worker.py:generate_next_action` (:209-302, report echo :337-349).
**Signature:** `call_code_agent(self, task: str = None)` — an `@agent_action` like any other; result dict `{task_instruction, completion_reason, summary, execution_history, steps_executed, budget}`.
**Data Shape:** The ACI object doubles as the mailbox: `grounding_agent.last_code_agent_result` holds the report; the worker formats it into the NEXT generator message (task, steps completed/max, completion reason, summary, per-step code history re-fenced), then resets it to None (:302).

### Decisive source
```python
# grounding.py — subtask vs full-task discrimination
if task is not None:
    task_to_execute = task            # SPECIFIC subtask
else:
    task_to_execute = self.current_task_instruction  # FULL task verbatim — never reworded
result = self.code_agent.execute(task_to_execute, screenshot, self.env.controller)
self.last_code_agent_result = result
return "import time; time.sleep(2.222)"   # action string while code agent works

# worker.py — consume-once
if hasattr(self.grounding_agent, "last_code_agent_result") and ... is not None:
    ...  # format into generator_message
    self.grounding_agent.last_code_agent_result = None   # reset after adding to context
```

**Flow:** worker plan contains `agent.call_code_agent()` (or with a subtask string) → eval calls the ACI method → CodeAgent runs its own budget loop synchronously → report stored on the ACI → method returns a sleep string as its action → next turn, the worker injects the formatted report into the generator prompt and clears the mailbox.
**Invariant:** (1) Full-task delegation must pass the ORIGINAL instruction unmodified (`current_task_instruction` set via `set_task_instruction` from the worker each turn :183-184) — docstring bans rewording to prevent hallucination drift. (2) `call_code_agent` is auto-removed from the API surface when env/controller is absent (worker reset skip list). (3) Exactly-once consumption: cleared immediately after formatting, so a report is never echoed twice even across retries. (4) The sleep-string return keeps the one-action-per-turn grammar intact while real work happened inside the call.
**Probe:** `grep -n 'self.last_code_agent_result' gui_agents/s3/agents/grounding.py gui_agents/s3/agents/worker.py` → grounding :227/:588 + worker :211-214/:302/:344-346.
**Probe:** `grep -n "skipped_actions.append" gui_agents/s3/agents/worker.py` → :73.
**Probe:** `grep -n 'set_task_instruction' gui_agents/s3/agents/worker.py gui_agents/s3/agents/grounding.py` → worker :184, grounding def :332-334.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-agent-s", query: "call_code_agent last_code_agent_result", limit: 5 });
```

## Verdict
Adopt attribute-mailbox handoff with structured reports and consume-once semantics for embedding a subagent inside a single agent-action; adapt report fields and the sleep placeholder; omit OSWorld controller specifics. This is the cleanest pattern in the repo for hierarchical delegation without a planner.

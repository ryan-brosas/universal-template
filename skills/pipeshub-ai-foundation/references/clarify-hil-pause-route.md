<!-- capsule-v2 -->
# clarify (HIL pause as a special route over obs.handle_clarify)

## Source
pipeshub-ai Apache-2.0 `main@4a02110d`; Codebase Memory `pipeshub-ai`. **Question:** What is the minimal correct wiring for an agent-initiated clarification pause, and why can't it be a plain execute()?

## Path/Symbol
`tools/builtin/coordination/clarify.py` — whole file, 61L. `handle()` = write_state("waiting_hil") → timeline "hil_pause" → `return await obs.handle_clarify(agent, call, ctx.goal, ctx.messages, ctx.turn_index)` (:51–58).

## Signature
Args `{question (required), context?}`. All mechanics delegated to `agent/observability.py::handle_clarify` — the tool is a thin route adapter.

## Data Shape
State transitions: `waiting_hil` state + timeline event BEFORE the blocking wait; handle_clarify owns HIL submission, the pause checkpoint (dual-id: hil_request_id + pending original call.id), and resume-completion of this ToolMessage.

### Decisive source
```python
async def handle(self, call: ToolCall, ctx: RouteContext) -> CoreToolResult:
    agent = ctx.agent
    await obs.write_state(agent, ctx.goal, "waiting_hil", ...)
    await obs.append_timeline(
        agent, "hil_pause", f"Waiting for clarification: {call.arguments.get('question', '')[:80]}",
        "waiting_hil", {"question": call.arguments.get("question", "")},
    )
    return await obs.handle_clarify(agent, call, ctx.goal, ctx.messages, ctx.turn_index)

async def execute(self, **kwargs: Any) -> ToolOutput:
    raise ToolError("clarify is a special route ... must not be executed directly")
```

**Flow:** agent hits ambiguity → clarify tool → state/timeline recorded → blocking HIL wait inside observability → answer returns as the tool result → run continues with the clarification in context. Contrast with task_complete's needs_input field: needs_input ESCALATES at completion without pausing; clarify PAUSES mid-run to continue after the answer.

**Invariant:** Blocking interactive waits require run context (messages/checkpoint/identity) that only special-route dispatch provides — hence sentinel execute(). State+timeline land BEFORE the await: if the process dies while waiting, the persisted state already says waiting_hil (resume path finds the pause).

**Probe:** No dedicated unit test (coverage caveat): handle_clarify's dual-id pause/resume contract pinned via hil-pause-resume-identity test suite; this file adds only ordering (state-before-wait), verified by source inspection.

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph --project pipeshub-ai --semantic-query '["ClarifyTool","handle_clarify","waiting_hil"]'
```

## Verdict
Adopt thin-route-over-observability shape and record-state-before-blocking-wait ordering; distinguish clarify (pause-and-continue) from needs_input (complete-and-escalate) when porting both.

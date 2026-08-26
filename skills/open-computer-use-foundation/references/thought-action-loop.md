<!-- capsule-v2 -->
# Thought→action loop — what is the exact turn order, and which messages enter history vs only the transcript?

**Source:** open-computer-use Apache-2.0 `master@610bac85`; Codebase Memory `ext-open-computer-use`. **Question:** What does one agent turn look like — in what order are vision-thought, action model call, tool execution and observations sequenced, and what exactly is appended to message memory?

## run() while-loop with keep-alive timeout refresh
**Path/Symbol:** `os_computer_use/sandbox_agent.py:171-215` (`SandboxAgent.run`).
**Signature:** `run(self, instruction)`; inner calls `action_model.call([system, *messages, thought_msg, "I will now use tool calls…"], tools)`.
**Data Shape:** `self.messages` holds ONLY user objectives (`"OBJECTIVE: …"`), assistant thoughts (when the action model returns text), tool calls re-serialized as `json.dumps(tool_call)`, and observation strings. The vision-thought message is constructed fresh EVERY turn and never stored.

### Decisive source
```python
while should_continue:
    # Stop the sandbox from timing out
    self.sandbox.set_timeout(60)
    content, tool_calls = action_model.call(
        [Message("You are an AI assistant with computer use abilities.", role="system"),
         *self.messages,
         Message(logger.log(f"THOUGHT: {self.append_screenshot()}", "green")),
         Message("I will now use tool calls to take these actions, or use the stop command if the objective is complete."),
        ], tools)
```

**Flow:** append objective → per turn: (1) `sandbox.set_timeout(60)` keep-alive FIRST → (2) build ephemeral context = system + history + FRESH screenshot-thought + action preamble → (3) call action model with tools → (4) append returned text as `THOUGHT` if any → (5) execute each tool call in order, breaking on `stop`, appending each call as JSON and its result as `OBSERVATION` → repeat.
**Invariant:** History contains no images — screenshots reach the model only through the ephemeral vision-thought turn, so memory stays text-only and bounded; `should_continue = name != "stop"` means ANY other tool result keeps the loop alive, and a missing/failed stop can loop indefinitely (keep-alive exists precisely for this).
**Probe:** `cd /mnt/hdd/utopia/inspo/external/open-computer-use && grep -n 'set_timeout(60)' os_computer_use/sandbox_agent.py && sed -n '171,216p' os_computer_use/sandbox_agent.py` (pins keep-alive placement before the model call and full turn order); direct harness: `tests/sandbox_agent.py` runs this exact loop against MockSandbox.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-open-computer-use", query: "run instruction should_continue sandbox timeout", limit: 8, fields: ["signature", "name", "file"] });
// expect ext-open-computer-use.os_computer_use.sandbox_agent.SandboxAgent.run
```

## Verdict
Adopt the four-slot turn shape (objective / thought / tool-call / observation), text-only memory with an ephemeral vision turn, and keep-alive-before-inference; adapt the 60s timeout value to your sandbox vendor; omit the fixed single-sandbox lifetime if you need resumable sessions (this design assumes one sandbox per process run).

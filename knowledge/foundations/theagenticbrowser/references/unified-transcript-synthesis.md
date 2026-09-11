<!-- capsule-v2 -->
# Unified OpenAI-format transcript — how do you log a multi-agent run as ONE coherent conversation when the agents never talk to each other?

**Source:** TheAgenticBrowser (TheAgentic Community License 1.0) `main@71daa28`; Codebase Memory `mnt-hdd-utopia-inspo-TheAgenticBrowser`. **Question:** How do you synthesize planner decisions and screenshot analyses into valid OpenAI message sequences so the whole task replays as one chat?

## Pseudo-tool-call synthesis per agent; real part-walk for the browser agent
**Path/Symbol:** `core/utils/openai_msg_parser.py`:`AgentConversationHandler` (`:21-217`: `_extract_tool_call` :28, `_extract_from_model_request` :63, `add_planner_message` :106, `add_ss_analysis_message` :146, `add_critique_message` :177), `ConversationStorage` (`:220-293`).
**Signature:** `add_browser_nav_message(browser_response)` / `add_planner_message(planner_response)` / `add_ss_analysis_message(ss_analysis_response)` / `add_critique_message(critique_response)` / `get_conversation_history()`.
**Data Shape:** One flat list of OpenAI-role dicts. Planner/SS-analyzer become FAKE assistant tool_calls (`name='planner_agent'`, `name='ss_analyzer'`, uuid ids) each immediately followed by a matching role:'tool' reply carrying the payload — structure the provider format demands, semantics the repo invented. The critique lands as a plain assistant message with `{feedback, final_response}` JSON content. The browser agent is extracted FOR REAL by walking pydantic-ai parts (`tool-call` → assistant w/ tool_calls via args_json parse w/ raw_args fallback; `tool-return` → role tool; `text` → assistant named 'browser_nav_agent').

### Decisive source
```python
def add_planner_message(self, planner_response):
    ...
    tool_call_id = str(uuid.uuid4())
    self.conversation_history.append({
        'role': 'assistant', 'content': None,
        'tool_calls': [{'id': tool_call_id, 'type': 'function',
                        'function': {'name': 'planner_agent',
                                     'arguments': json.dumps({'plan': plan, 'next_step': next_step})}}]})
    self.conversation_history.append({
        'role': 'tool', 'tool_call_id': tool_call_id, 'name': 'planner_agent',
        'content': json.dumps({'plan': plan, 'next_step': next_step})})
```
Storage side (`ConversationStorage.save_conversation`): lazily mints `<prefix>_conversation_<timestamp>.json` ONCE per instance, then on every save reads the existing file and appends only `serializable_messages[len(existing):]` — a prefix-diff against its OWN last write, so calling save repeatedly with the full accumulated history stays append-only.
**Flow:** orchestrator calls one adder per agent turn → after critique, `get_conversation_history()` → `save_conversation(..., prefix="task")` → single growing JSON file under the per-run `task_N` folder.
**Invariant:** Every synthesized tool_call MUST get an immediate tool reply or the transcript fails provider validation — the pairing is atomic. uuid4 ids are safe precisely because these calls never round-trip to a real model. The prefix-diff assumes history only ever GROWS in place; reordering or trimming breaks the diff silently.
**Probe:** No tests (coverage caveat). Graph pin: `trace_path --function-name add_ss_analysis_message --direction inbound` resolves to `Orchestrator.run`; `AgentConversationHandler._extract_from_model_request` appears as a direct callee of run.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-TheAgenticBrowser", query: "conversation handler planner ss_analyzer storage", limit: 10, fields: ["name", "file"] });
```

## Verdict
Adopt pseudo-tool synthesis for logging non-LLM decision points into a unified trace. Adapt names/schema of the synthetic tools to your pipeline. Omit the file-append storage if you have real telemetry (logfire is already wired) — but keep the pairing invariant wherever transcripts must replay.

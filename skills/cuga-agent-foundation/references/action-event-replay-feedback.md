<!-- capsule-v2 -->
# ActionAgentEventProcessor replay feedback — how are browser tool calls played back with per-action outcomes recorded instead of raised?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** What does the demo/replay executor do per tool call, which config keys inject page/provider dependencies, and how do Alert results differ from exceptions?

## Config-carried page injection with feedback-log outcomes
**Path/Symbol:** `src/cuga/backend/cuga_graph/utils/event_porcessors/action_agent_event_processor.py:ActionAgentEventProcessor.play_tool_async` (:160-220), `collect_feedback` (:222-244).
**Signature:** `play_tool_async(page, tool_def: Dict, element_name, tool_provider: BrowserToolImplProvider, session_id=None, page_data=None, communicator=None)`; `collect_feedback(action_name, element_name, args, error_message, is_alert=False)`.
**Data Shape:** feedback entries `{action, status: 'alert'|'error'|'success', element_id: args['bid'] or '', element_name, message}`; routed actions: go_back / click / open_app / type / select_option (+ silent no-op `update_plan`).

### Decisive source
```python
            config = {"configurable": {"page": page, 'demo_mode': 'off', 'tool_impl': tool_provider}}
            if page_data:
                config["configurable"]["page_data"] = page_data
                if communicator:
                    config["configurable"]["communicator"] = communicator
            ...
            await asyncio.sleep(4)
            tracker.actions_count += 1
            if isinstance(res, Alert):
                self.collect_feedback(action_name, element_name, args, error_message=res.message, is_alert=True)
            else:
                self.collect_feedback(action_name, element_name, args, error_message="")
        except Exception as e:
            self.collect_feedback(action_name, element_name, args, str(e))
```

**Flow:** clean (identity) → per tool_call: name-lowered dispatch to langchain tool `.ainvoke(input=args, config=config)` where page/demo_mode/tool_impl (and extension page_data+communicator) ride RunnableConfig.configurable — the SAME injection seam the pass-18 tools already expect → fixed 4s settle sleep → `tracker.actions_count += 1` (the counter PlannerNode's ≥4 reset watches) → outcome recorded as alert (Alert INSTANCE, not exception), success, or error string.
**Invariant:** NOTHING raises to the caller — all failures become feedback rows; replay must survive a whole batch of actions. Alert-vs-error distinction matters because alerts are model-visible page states, not infra failures. The `action_name.lower()` dispatch means tool names are case-insensitive here but the config keys are not.
**Probe:** Recorded upstream gap. Deterministic: `grep -n "demo_mode" src/cuga/backend/cuga_graph/utils/event_porcessors/action_agent_event_processor.py | head -2` shows the config key.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "ActionAgentEventProcessor play_tool_async collect_feedback BrowserToolImplProvider", limit: 6, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt configurable-dict dependency injection for page-bound tools and never-raise replay with typed outcome logs. Adapt the settle delay and action set. Omit the dead sync play_tool path (upstream keeps it commented out).

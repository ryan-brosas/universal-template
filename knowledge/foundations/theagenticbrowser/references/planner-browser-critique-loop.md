<!-- capsule-v2 -->
# Planner→Browser→Critique loop — where does termination authority, error tolerance, and context-death handling live in a three-agent browser loop?

**Source:** TheAgenticBrowser (TheAgentic Community License 1.0) `main@71daa28`; Codebase Memory `mnt-hdd-utopia-inspo-TheAgenticBrowser`. **Question:** How do you structure a plan/execute/critique agent loop so the LLM decides termination but infrastructure errors never hang or crash the run?

## While-loop with per-agent history, critique-gated terminate, three-tier exception policy
**Path/Symbol:** `core/orchestrator.py`:`Orchestrator.run` (`:282-631`), `reset_state` (`:246-259`), `cleanup` (`:660-671`); agents `core/agents/planner_agent.py:213-222`, `core/agents/critique_agent.py:102-111`, `core/agents/browser_agent.py:229-238`.
**Signature:** `async def run(self, command, start_url: Optional[str] = None) -> str`.
**Data Shape:** Three independent pydantic-ai `Agent`s sharing one OpenAI-compatible model env (`AGENTIC_BROWSER_TEXT_MODEL`): PA returns `{plan, next_step}` (result_type), BA is tool-calling with `deps_type=current_step_class`, CA returns `{feedback, terminate: bool, final_response}`. Per-agent message histories live in `self.message_histories['planner'|'browser'|'critique']`; per-agent cumulative token meters in `cumulative_tokens`.
**Loop body per iteration:** planner.run(user_prompt w/ query+previous-plan+feedback, validated planner history) → notify PLAN once (iteration 1 only) + STEP every time → optional pre-action screenshot → BA.run(step as prompt, current_step deps, DOM-filtered history) → extract tool interactions → optional post-action screenshot + VLM diff analysis → CA.run(plan/step/tool_response/interactions/ss_analysis/browser_error, full critique history — never filtered) → persist transcript → if terminate: return final_response; else rebuild PA prompt with critique feedback.

### Decisive source
```python
except Exception as e:
    error_str = str(e)
    if "context_length_exceeded" in error_str or "maximum context length" in error_str:
        ...
        final_response = "Task could not be completed due to conversation length limitations..."
        await self.response_handler(final_response)
        return final_response                      # graceful death for ALL THREE agents
    else:
        browser_error = str(e)                     # browser failures become CRITIQUE INPUT:
        ...                                        # f'browser_error="{browser_error}"'
# step-level catch-all:
except Exception as step_error:
    ...
    continue                                       # retry same command, next iteration
```
Termination authority is 100% the critique's LLM decision (`if critique_response.data.terminate`) — there is NO max-iteration cap in code; the CA system prompt encodes soft caps instead ("loop ≥5 times → terminate", "≥7 different ways tried → terminate", and rule #2 forbids concluding success after one step).
**Flow:** reset_state (session-aware: persistent sessions keep histories) → run loop → cleanup forked on input_mode/session (full teardown vs partial preserve).
**Invariant:** Browser errors are DATA fed to the critic; planner/critique errors are FATAL (re-raised as PlannerError / raw); context-length is a graceful structured exit from any of the three stages. The string-match on error text is deliberate provider-agnosticism (works across OpenAI-compatible backends). Never filter the critique's history — its cross-iteration memory is what detects loops.
**Probe:** No tests (coverage caveat). Graph pin: `trace_path --function-name run --direction outbound --depth 2` shows exactly 50 callees incl. all four filter/extract helpers, both screenshot calls, and the three conversation_handler adders.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-TheAgenticBrowser", query: "Orchestrator run planner critique terminate", limit: 10, fields: ["name", "file"] });
```

## Verdict
Adopt the three-tier error taxonomy and critique-owned termination. Adapt the soft-cap phrasing and add a hard iteration ceiling for production. Omit logfire/GUI notification plumbing unless you run the overlay UI.

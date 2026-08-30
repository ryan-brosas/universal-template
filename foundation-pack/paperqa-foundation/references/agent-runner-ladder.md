<!-- capsule-v2 -->
# Agent runner ladder — which backend executes a query, when is the index prebuilt, and how does status get normalized on timeout or failure?

**Source:** paper-qa (Apache-2.0) `main@57e89f7223b0960d5ee5ea048c69e3c47e088572`; Codebase Memory `paper-qa`. **Question:** How does `run_agent` choose between fake/aviary/ldp backends, why is the directory index built before the rollout starts, and what statuses can emerge from a wrapped rollout?

## Connected graph-selected seam
**Path/Symbol:** `src/paperqa/agents/main.py:run_agent` (:91-148), `_run_with_timeout_failure` (:151-179), `run_fake_agent` (:182-256); `src/paperqa/agents/__init__.py:ask` (:105-112).
**Signature:** `async def run_agent(docs, query, settings, agent_type: str | type = DEFAULT_AGENT_TYPE, **runner_kwargs) -> AnswerResponse`; `async def _run_with_timeout_failure(rollout, settings, env) -> tuple[PQASession, AgentStatus]`.
**Data Shape:** Returns `AnswerResponse(session, status)`; status ∈ AgentStatus {SUCCESS, UNSURE, TRUNCATED, FAIL}. Dispatch order: `"fake"` string → aviary tool-selector (`settings.make_aviary_tool_selector(agent_type)`) → ldp agent (`await settings.make_ldp_agent(agent_type)`) → NotImplementedError.

### Decisive source
```python
# Build the index once here, and then all tools won't need to rebuild it
if PaperSearch.TOOL_FN_NAME in (settings.agent.tool_names or DEFAULT_TOOL_NAMES):
    await get_directory_index(settings=settings, build=settings.agent.rebuild_index)

if isinstance(agent_type, str) and agent_type.lower() == FAKE_AGENT_TYPE:
    session, agent_status = await run_fake_agent(query, settings, docs, **runner_kwargs)
elif tool_selector_or_none := settings.make_aviary_tool_selector(agent_type):
    session, agent_status = await run_aviary_agent(...)
elif ldp_agent_or_none := await settings.make_ldp_agent(agent_type):
    session, agent_status = await run_ldp_agent(...)
else: raise NotImplementedError(...)

if agent_status != AgentStatus.TRUNCATED and session.has_successful_answer is False:
    agent_status = AgentStatus.UNSURE
...
async with asyncio.timeout(settings.agent.timeout): status = await rollout()
except TimeoutError: status = AgentStatus.TRUNCATED
except Exception:    logger.exception("Trajectory failed."); status = AgentStatus.FAIL
if status == AgentStatus.TRUNCATED or not env.state.query_tool_history(GenerateAnswer.TOOL_FN_NAME):
    ... synthesize ToolRequestMessage calling GenerateAnswer; env.exec_tool_calls(...)
```

**Flow:** prebuild index ONLY if a search tool is configured (fake agent included — it also calls search) → dispatch backend → each backend's rollout runs inside `_run_with_timeout_failure`, which converts timeout→TRUNCATED and crash→FAIL, then guarantees a GenerateAnswer attempt exists (failover synthesis for TRUNCATED or never-called) → post-normalization demotes finished-but-unsuccessful runs to UNSURE. The fake agent's rollout is a fixed script: LLM-proposed searches → gather_evidence → generate_answer → LLM-selected complete.
**Invariant:** The index prebuild happens BEFORE any backend runs so tools share one warm index (per-process tantivy open-cache makes this cheap); `rebuild_index=False` propagates into that prebuild's `build=` flag, connecting the "please rebuild" RuntimeError to user config. A run NEVER ends without a GenerateAnswer attempt while its environment is alive — but FAIL from a trajectory exception still returns normally (no raise), so callers must branch on status, not exceptions. UNSURE demotion applies only to non-TRUNCATED outcomes because TRUNCATED already carries its own retry semantics upstream.
**Probe:** `tests/test_agents.py::test_timeout` (:482-509) — 0.05s timeout forces TRUNCATED, answer contains CANNOT_ANSWER_PHRASE, and the last tool response shows the agent was shown the failure specifics ("no papers"); :475/:540 pin SUCCESS for healthy aviary/fake runs; `::test_empty_index_without_index_rebuild` (:1079-1089) pins the prebuild guard surfacing through `agent_query(rebuild_index=False)`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "paper-qa", query: "run_agent make_aviary_tool_selector make_ldp_agent AgentStatus has_successful_answer", limit: 10 });
// trace_path --function-name _run_with_timeout_failure --direction inbound → run_fake_agent, run_aviary_agent, run_ldp_agent
```

## Verdict
Adopt the three-stage backend dispatch (scripted-fake → tool-selector → full agent object) and the wrap-with-guaranteed-answer-attempt pattern plus explicit status algebra for any tool-loop product; adapt backend factories to your harness's agent SPI; omit ldp entirely without an RL training stack. Relationship note: this capsule owns DISPATCH/STATUS; `agent-tool-loop-status.md` retains the in-loop question-swap/cursor mechanics and cites the same failover function from the tool side. Coverage caveat: cited paths `no_recorded_issue` + `metadata_match`.

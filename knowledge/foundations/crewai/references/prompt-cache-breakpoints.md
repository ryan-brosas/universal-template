<!-- capsule-v2 -->
# Prompt-cache breakpoints — where are cache_control markers placed so ReAct loops hit the provider prompt cache?

**Source:** crewAI MIT `main@f4731f5025f861c78e3af0487cc80bf5e7c64782`; Codebase Memory `ext-crewAI`. **Question:** Which two messages get cache breakpoints at executor setup, and why those two?

## mark_cache_breakpoint usage in _setup_messages
**Path/Symbol:** `lib/crewai/src/crewai/experimental/agent_executor.py:310-335` (`_setup_messages`, mirrored in deprecated `agents/crew_agent_executor.py:170-206`); `lib/crewai/src/crewai/llms/cache.py:27-37` (`mark_cache_breakpoint` / `strip_cache_breakpoint`).
**Signature:** `mark_cache_breakpoint(message: LLMMessage) -> LLMMessage` (adds provider-agnostic marker; Anthropic layer converts to `cache_control`).
**Data Shape:** Applies ONLY to the initial setup messages; loop-appended messages never carry breakpoints.

### Decisive source
```python
if isinstance(self.prompt, SystemPromptResult):
    system_prompt = self._format_prompt(self.prompt["system"], inputs)
    user_prompt = self._format_prompt(self.prompt["user"], inputs)
    # Cache breakpoints: end-of-system caches the per-agent stable
    # prefix; end-of-user caches the per-task stable prefix across
    # ReAct-loop iterations.
    self.state.messages.append(mark_cache_breakpoint(
        format_message_for_llm(system_prompt, role="system")))
    self.state.messages.append(mark_cache_breakpoint(
        format_message_for_llm(user_prompt)))
```

**Flow:** Executor builds [system★, user★] (or single prompt → [user★]) before the loop; every later iteration re-sends the same prefix with growing suffix — the two stars let providers cache (1) the agent persona/tools block and (2) the task instruction block, so per-iteration cost is only the delta. Tests pin stamping behavior per provider shape (`TestAnthropicCacheStamping.test_stamps_system_with_cache_control`, `test_unmarked_messages_get_no_cache_control`).
**Invariant:** Breakpoints belong on the LAST message of each stable prefix segment, not on every message (providers cap control markers — Anthropic allows 4 blocks); stripping happens centrally (`strip_cache_breakpoint`) when a provider doesn't support caching, so executors can mark unconditionally.
**Probe:** Deterministic anchors at this pin: `grep -n 'mark_cache_breakpoint' lib/crewai/src/crewai/experimental/agent_executor.py` → lines 316(import), 322, 327; `grep -n 'def mark_cache_breakpoint' lib/crewai/src/crewai/llms/cache.py` → line 27. Behavior pinned by `tests/llms/test_prompt_cache.py::TestAnthropicCacheStamping` (4 tests).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-crewAI", query: "mark_cache_breakpoint llms cache", limit: 5, detail: "ids" });
```

## Verdict
Adopt two-segment breakpoint placement (agent-stable, task-stable); adapt marker encoding to your provider SDK; omit entirely for providers without prompt caching (markers strip cleanly).

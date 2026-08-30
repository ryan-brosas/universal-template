<!-- capsule-v2 -->
# Coordinator system-message sandwich — How do you inject framework instructions into a user-provided agent without destroying their prompt?

**Source:** CAMEL-AI/camel Apache-2.0 `master@13dc7a7d`; Codebase Memory `ext-camel`. **Question:** When a caller supplies a custom coordinator_agent, exactly how is its system message merged with the workforce's own?

## Append, never replace
**Path/Symbol:** `camel/societies/workforce/workforce.py:Workforce.__init__` coordinator setup (:402-460).
**Signature:** `Workforce(description, coordinator_agent: Optional[ChatAgent] = None, new_worker_agent=None, default_model=None, ...)`.
**Data Shape:** Default path builds ChatAgent with fixed "Workforce Manager" sys_msg; custom path concatenates contents.

### Decisive source
```python
else:
    logger.info("Custom coordinator_agent provided. Preserving user's "
        "system message and appending workforce coordination "
        "instructions to ensure proper functionality.")
    if coordinator_agent.system_message is not None:
        user_sys_msg_content = coordinator_agent.system_message.content
        # ... appended after the coordination instructions
```

**Flow:** no agent → warn + build default (ModelPlatformType.DEFAULT) → custom agent → the workforce coordination instructions are kept AND the user's system message content is APPENDED, so assignment prompts still carry "assign tasks to an existing worker, creating a new worker for a task" behavior regardless of what persona the caller chose. The same preservation instinct shows in `_find_assignee`'s unconditional `self.coordinator_agent.reset()` before each batch (:4088) — memory hygiene is enforced at call sites because the agent instance is user-owned.
**Invariant:** The coordination contract text must reach the model on EVERY path; silently swapping the system message would break ASSIGN_TASK_PROMPT adherence while looking like a working integration.
**Probe:** `grep -c "Preserving user's" camel/societies/workforce/workforce.py` → 2 (coordinator_agent :424 AND task_agent twin :484 — the same sandwich is applied to both injected agents).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-camel", query: "coordinator_agent system_message Workforce Manager default", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt append-don't-replace for host-injected instructions into user agents. Adapt wording. Omit default-model plumbing.

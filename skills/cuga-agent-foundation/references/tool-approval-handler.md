<!-- capsule-v2 -->
# ToolApprovalHandler — the shared post-codegen approval interrupt/resume cycle (adapter-parameterized)

**Source:** cuga-agent Apache-2.0 `main@5de53ade`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** After the model generates code, a policy may require human approval before it runs. The approval must interrupt, survive a HITL round-trip, resume by re-running the SAME code exactly once, and record an auditable decision — identically for Lite and Supervisor. What state flags and metadata shape make that cycle safe?

## The handler
**Path/Symbol:** `src/cuga/backend/cuga_graph/nodes/cuga_agent_core/policy/tool_approval_handler.py` (`ToolApprovalHandler` :25-300).
**Signature:** static methods `should_skip_policy_check(adapter, state)`, `is_returning_from_approval(adapter, state)`, `extract_approved_code(adapter, state)`, `clean_approval_metadata(metadata)`, `handle_approval_resumption(adapter, state)`, `check_and_create_approval_interrupt(adapter, state, code, content, config)`, `_create_approval_interrupt(...)`, `_generate_approval_message(...)`, `handle_denial(adapter, state)`.
**Data Shape:** All read/write state via `adapter.get_metadata`/`set_metadata` (key = `adapter.metadata_key`) and `adapter.get_messages`/`execute_node_name`/`sender_name`, so the same handler is byte-identical for both graphs.

### Decisive source
```python
# tool_approval_handler.py:29-43 — the user_approved flag is the skip/resume gate
def should_skip_policy_check(adapter, state):
    md = adapter.get_metadata(state)
    return bool(md and md.get("user_approved"))   # returning from approval: don't re-match the same policy
def is_returning_from_approval(adapter, state):
    md = adapter.get_metadata(state)
    return bool(md and md.get("user_approved") is True)

# tool_approval_handler.py:88-113 — resume re-runs the SAME code, then clears the temp fields
code = getattr(state, "script", None) or ToolApprovalHandler.extract_approved_code(adapter, state)
...
cleaned_metadata = ToolApprovalHandler.clean_approval_metadata(metadata)  # drops approval_required/user_approved/required_tools/matched_tools/required_apps/full_code/code_preview
return Command(goto=adapter.execute_node_name, update={"script": code, adapter.metadata_key: cleaned_metadata, "step_count": state.step_count + 1})
```

**Flow:** `call_model` checks `is_returning_from_approval` first and routes to `handle_approval_resumption` (priority over everything). Otherwise, when code is generated and `settings.policy.enabled`, `check_and_create_approval_interrupt` loads the policy system from config, builds context from state, and calls `agent.check_tool_approval_for_code(code, context)`. On a match it records an APPROVAL_REQUIRED decision, sets approval metadata (policy fields, required_tools/apps, approval_message, show_code_preview), and returns an interrupt Command routing to END with `hitl_action` + a markdown approval message + `script=code` + `sender`. On resume, the code is re-run via `execute_node_name`; on denial, `handle_denial` records a DENIED decision and ENDs with "Execution cancelled by user." The approval message renders required tools (`["*"]` → "All tools"), apps, and a code preview.
**Invariant:** The `user_approved` flag is the single source of truth for skip/resume — it must be set in metadata by the HITL handler (Lite's `CugaLiteHumanInTheLoopHandler._handle_tool_approval`) and cleared by `clean_approval_metadata` after resume so the next generated code can trigger approval again. `extract_approved_code` re-derives code from the last AI message as a fallback when `state.script` is gone. Any error in the policy check is caught and returns None (fail-open — never block execution on a policy-system bug).
**Probe:** `tests/policy/test_tool_approval_adapter.py` (229L) and `tests/policy/test_execution_policy.py` (274L) pin the adapter-parameterized approval/resume/denial paths; full-graph e2e under `policy/tests/test_tool_approval_full_graph.py`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "ToolApprovalHandler user_approved check_tool_approval_for_code handle_approval_resumption", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the user_approved skip/resume gate, the metadata temp-field lifecycle (set on interrupt, cleared on resume), the fail-open policy-check error path, and the adapter-parameterized handler so one implementation serves both graphs. Adapt the approval-message wording and the HITL action model to your product. Omit the policy-system coupling if you gate approval by a simpler rule.

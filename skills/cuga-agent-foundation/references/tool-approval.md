<!-- capsule-v2 -->
# Tool Approval — human-in-the-loop gate that fires after code generation, not at intent time

**Source:** cuga-agent Apache-2.0 `main@5de53ade`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** How do you require per-user approval before generated agent code touches dangerous tools, and how do you resume exactly-once after the user answers?

## Post-codegen scan → interrupt → approved/denied resumption
**Path/Symbol:** `src/cuga/backend/cuga_graph/policy/agent.py:1291-1402` (`check_tool_approval_for_code`, `_check_code_uses_tools`); interrupt/resume in `src/cuga/backend/cuga_graph/nodes/cuga_agent_core/policy/tool_approval_handler.py` (`should_skip_policy_check` :29-37, `handle_approval_resumption` :84-113, `check_and_create_approval_interrupt` :116-181, `handle_denial` :262-300); stage note `models.py:282-284`.

**Signature:** `async check_tool_approval_for_code(code: str, context: PolicyContext) -> Optional[PolicyMatch]` (confidence pinned to 1.0, highest-priority policy wins).

**Data Shape:** Policy carries `required_tools: List[str]` ("*" wildcard allowed), `required_apps`, `approval_message`, `show_code_preview: bool = True`. Metadata gains `approval_required / user_approved / required_tools / matched_tools / full_code / code_preview`.

### Decisive source
```python
# tool_approval_handler.py:29-37 — the exactly-once gate
@staticmethod
def should_skip_policy_check(adapter, state) -> bool:
    md = adapter.get_metadata(state)
    return bool(md and md.get("user_approved"))
# Resumption (:88): code = getattr(state, "script", None) or extract_approved_code(...)
# then clean_approval_metadata strips approval_* fields before goto execute_node.
# Denial (:262-279): user_approved is False ⇒ END with
#   "Execution cancelled by user." + DENIED decision record.
```
Code-scan shape (`agent.py:1380-1384`): `"*" in required_tools` matches any `re.findall(r'(\w+)\s*\(', code)`; named tools match substring presence plus app-prefix calls `\b{app}_\w+\s*\(`. Highest priority wins on multiple matches (:1337).

**Flow:** codegen node produced code → handler asks policy system to scan it → match ⇒ metadata + HITL action + markdown approval message (policy name, tools/apps lists, fenced python preview) → `Command(goto=END, update={..., "hitl_action": ..., "sender": adapter.sender_name})` interrupts the run → user approves ⇒ next invocation skips ALL policy checks (`user_approved`), re-extracts or reuses `script`, records APPROVED decision, strips approval fields, `goto=execute_node` → user denies ⇒ END with cancellation answer.

**Invariant:** The skip gate is what makes resumption terminate: without it, the same ToolApproval policy would re-match the same code forever (the check runs every pass of `prepare_tools_and_apps`). And `clean_approval_metadata` must remove `user_approved` on the way to execution so a *subsequent* new task on the thread is governed again.

**Probe:** `tests/unit/` and e2e coverage via `test_e2e_tool_enrichment.py` for the shared adapter seams; direct probes for the runtime ladder live in `tests/unit/test_toolguard_provider.py`. Caveat: no dedicated unit file pins `handle_denial`; its behavior is exercised through supervisor/Lite integration flows — read `tool_approval_handler.py:262-300` directly when porting.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "check_and_create_approval_interrupt user_approved resumption", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt post-codegen scanning (intent-time checks can't see what the model actually wrote), the interrupt-with-preview Command shape, and the one-shot `user_approved` gate with field cleanup. Adapt the regex scan into an AST walk if your codegen emits parseable Python. Omit auto_approve_after unless your host has a scheduler to enforce it.

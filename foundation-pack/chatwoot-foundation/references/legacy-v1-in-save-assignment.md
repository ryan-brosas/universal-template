<!-- capsule-v2 -->
# Legacy V1 in-save assignment — why must auto-assignment on status change run inside before_save on a locked row?

**Source:** Chatwoot MIT `develop@6154aebcfea1fe62e8dd01fbf94568ef827fc51c`; Codebase Memory `ext-chatwoot`. **Question:** How does assigning an agent during a status transition stay atomic and avoid duplicate events when writers race?

## Lock-and-reconcile in-memory mutation
**Path/Symbol:** `app/services/auto_assignment/agent_assignment_service.rb:AutoAssignment::AgentAssignmentService#assign_under_lock` (lines 15-28) with helpers `discard_already_applied_status_change` (44-48) and `reassignment_still_needed?` (53-59); caller `app/models/concerns/auto_assignment_handler.rb:run_legacy_auto_assignment` (15-21).
**Signature:** `assign_under_lock -> assignee|nil` (mutates the conversation IN MEMORY, no save); `perform` wraps it in `Conversation.transaction { conversation.save if assign_under_lock }`.
**Data Shape:** operates on the CALLER's in-memory conversation object; reads a fresh `Conversation.lock.find_by(id:)` as reconciliation truth.

### Decisive source
```ruby
def assign_under_lock
  locked = Conversation.lock.find_by(id: conversation.id)
  return unless locked

  discard_already_applied_status_change(locked)
  return unless reassignment_still_needed?(locked)

  new_assignee = find_assignee
  return unless new_assignee

  conversation.assignee_id = locked.assignee_id
  conversation.clear_attribute_changes([:assignee_id])
  conversation.assignee = new_assignee
end

def discard_already_applied_status_change(locked_conversation)
  return unless conversation.will_save_change_to_status? && conversation.status == locked_conversation.status

  conversation.clear_attribute_changes([:status])
end
```

**Flow:** conversation opens (before_save, V1 path) → lock the row FOR UPDATE → if a concurrent writer already committed the same status while we waited on the lock, DROP our now-duplicate dirty status change (`clear_attribute_changes`) so after_commit announces it once → re-check that reassignment is still needed against MERGED pending values: fields this save is writing win (`will_save_change_to_... ? conversation : locked`), untouched fields defer to the locked row → pick via round robin → write `assignee_id = locked.assignee_id` then clear its change tracking and set the association — so the subsequent save carries ONLY the genuinely-new assignee delta alongside our status change, and both commit atomically.
**Invariant:** Status and assignee must commit as ONE change-set: the in-source comment records that a follow-up save would reset saved_changes and HIDE the status change from after_commit callbacks (losing `conversation.opened`). The clear-then-set dance on assignee_id exists so Rails' dirty tracking reports exactly one clean assignment change. The bot-handoff nuance is pinned in-source: `bot_handoff!` clears the agent bot in the same save that opens, and the merged-pending-value check respects it.
**Probe:** `grep -n 'clear_attribute_changes' app/services/auto_assignment/agent_assignment_service.rb` → lines 26 and 47 exactly; direct test `spec/services/auto_assignment/agent_assignment_service_spec.rb` ("keeps an existing AgentBot owner" line 30).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-chatwoot", query: "AgentAssignmentService assign_under_lock discard status change", limit: 5 });
```
Rank-1: `AutoAssignment::AgentAssignmentService.assign_under_lock app/services/auto_assignment/agent_assignment_service.rb 15-28`.

## Verdict
Adopt lock-read-reconcile-then-mutate-in-memory when an association must be assigned inside another attribute's save for callback visibility; adopt duplicate-change discard after lock wait. Adapt `.lock` to your ORM's pessimistic locking. Omit Chatwoot's V2-vs-V1 branching unless porting both planes.

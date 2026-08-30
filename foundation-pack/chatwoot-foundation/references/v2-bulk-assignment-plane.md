<!-- capsule-v2 -->
# V2 bulk assignment plane — how do triggers coalesce, stale backlog skip, and rows claim atomically?

**Source:** Chatwoot MIT `develop@6154aebcfea1fe62e8dd01fbf94568ef827fc51c`; Codebase Memory `ext-chatwoot`. **Question:** How does inbox-level auto-assignment v2 run at most one bulk pass at a time and assign each conversation exactly once under concurrency?

## Token-gated single-flight job + SKIP LOCKED claim
**Path/Symbol:** `app/jobs/auto_assignment/assignment_job.rb:AutoAssignment::AssignmentJob.enqueue_for_inbox` (lines 6-22) + `release_in_flight` (44-50); `app/services/auto_assignment/assignment_service.rb:claim_and_assign` (109-124) + `unassigned_conversations` (35-50).
**Signature:** `enqueue_for_inbox(inbox_id) -> bool` (false when another pass in flight); `claim_and_assign(conversation, agent) -> bool`.
**Data Shape:** Redis key `AUTO_ASSIGNMENT_IN_FLIGHT_KEY % {inbox_id}` holding a SecureRandom uuid token, TTL 5 min (`IN_FLIGHT_TTL`); release via compare-and-delete only.

### Decisive source
```ruby
def self.enqueue_for_inbox(inbox_id)
  key = format(::Redis::Alfred::AUTO_ASSIGNMENT_IN_FLIGHT_KEY, inbox_id: inbox_id)
  token = SecureRandom.uuid
  return false unless ::Redis::Alfred.set(key, token, nx: true, ex: IN_FLIGHT_TTL)

  return true if perform_later(inbox_id: inbox_id, token: token)

  # Enqueue was halted; release our own claim so the inbox isn't gated until the TTL.
  ::Redis::Alfred.delete_if_equals(key, token)
  false
rescue StandardError
  ::Redis::Alfred.delete_if_equals(key, token)
  raise
end

# service — atomic per-row claim:
locked = inbox.conversations
              .where(id: conversation.id).unassigned
              .lock('FOR UPDATE SKIP LOCKED')
              .first
next false unless locked
locked.update!(assignee: agent)
```

**Flow:** any trigger (conversation opened/resolved/snoozed via `AutoAssignmentHandler#run_auto_assignment`, or `PeriodicAssignmentJob` sweep) → enqueue_for_inbox SETs NX+EX marker; if taken, this trigger is DROPPED (coalescing) → job performs one bulk pass over `inbox.conversations.unassigned.open` ordered by policy priority (`longest_waiting` reorders by last_activity_at else created_at), excluding rows older than `exclude_older_than_hours` (default **168h**, measured on `last_activity_at`, NOT created_at, so reopened conversations stay eligible) → for each candidate, `FOR UPDATE SKIP LOCKED` claims the still-unassigned row so two overlapping passes can never both assign it → after success the rate limiter records the assignment and ASSIGNEE_CHANGED is dispatched MANUALLY (`dispatch_assignment_event`) because the bulk update path doesn't ride the model callbacks' dispatcher wiring. ensure-block releases the in-flight marker with delete-if-equals-token, so a TTL-lapsed zombie cannot delete a newer job's claim.
**Invariant:** At most ONE AssignmentJob per inbox is queued-or-running (token gate); every row transition is guarded by an atomic DB claim independent of that gate ("the in-flight gate is best-effort and can lapse on TTL" — in-source comment); tokenless legacy jobs skip release rather than deleting someone else's marker.
**Probe:** `grep -n 'nx: true, ex: IN_FLIGHT_TTL' app/jobs/auto_assignment/assignment_job.rb` → line 12; `grep -n "lock('FOR UPDATE SKIP LOCKED')" app/services/auto_assignment/assignment_service.rb` → line 115; `grep -c 'delete_if_equals' app/jobs/auto_assignment/assignment_job.rb` → 3 (enqueue-halt, rescue, release). Direct test `spec/jobs/auto_assignment/assignment_job_spec.rb`.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "ext-chatwoot", query: "AssignmentJob enqueue_for_inbox token in-flight", limit: 5 });
```
Resolves the AutoAssignment::AssignmentJob / AssignmentService cluster line-exact.

## Verdict
Adopt NX+EX single-flight with token-scoped release plus a DB-level second line of defense (SKIP LOCKED) for the actual mutation; adopt activity-time-based staleness exclusion. Adapt queue/ORM idioms; keep manual event dispatch ONLY where your bulk writer bypasses model callbacks. Omit enterprise 'balanced' assignment_order unless porting the commercial tree.

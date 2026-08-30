<!-- capsule-v2 -->
# Round-robin Redis queue — how does a Redis list implement fair rotation with self-healing membership?

**Source:** Chatwoot MIT `develop@6154aebcfea1fe62e8dd01fbf94568ef827fc51c`; Codebase Memory `ext-chatwoot`. **Question:** How does assignment pick the next eligible agent fairly, survive membership drift, and respect online-only filtering?

## List-as-queue with set-equality self-heal
**Path/Symbol:** `app/services/auto_assignment/inbox_round_robin_service.rb:AutoAssignment::InboxRoundRobinService#available_agent` (lines 29-33) and `validate_queue?` (52-54).
**Signature:** `available_agent(allowed_agent_ids: []) -> User|nil`; key = `Redis::Alfred::ROUND_ROBIN_AGENTS % {inbox_id}`; values are STRING user ids (`lrange` returns strings; membership sources are integers).
**Data Shape:** Redis list per inbox in rotation order; allowed_agent_ids must be strings (callers map `.to_s`).

### Decisive source
```ruby
def available_agent(allowed_agent_ids: [])
  reset_queue unless validate_queue?
  user_id = get_member_from_allowed_agent_ids(allowed_agent_ids)
  inbox.inbox_members.find_by(user_id: user_id)&.user if user_id.present?
end

def get_member_from_allowed_agent_ids(allowed_agent_ids)
  return nil if allowed_agent_ids.blank?

  user_id = queue.intersection(allowed_agent_ids).pop
  pop_push_to_queue(user_id)
  user_id
end
```

**Flow:** pick request → validate_queue? compares `inbox_members.map(&:user_id).sort == queue.map(&:to_i).sort` — a SET-equality check (order-insensitive) that detects any drift (member added/removed, stale/missing ids) and triggers full reset from current membership → intersect the queue's rotation order with today's allowed ids (online ∩ members ∩ team) → `.pop` takes the LAST matching id → pop_push_to_queue immediately lrem+lpush it to the FRONT so the next pick rotates to a different agent.
**Invariant:** The intersection preserves the QUEUE's order, not the caller's array order — fairness comes from the stored rotation, eligibility from the caller's filter; the two are combined non-destructively. Queue maintenance is lazy: nothing keeps the list warm on membership change; every read self-heals via the sort-compare. Online filtering happens BEFORE this service (`online_agents.select { |_k,v| v.eql?('online') }` in AgentAssignmentService#online_agent_ids / InboxAgentAvailability) — an offline agent is simply absent from allowed ids that turn, and rejoins automatically when back online.
**Probe:** `grep -n 'intersection' app/services/auto_assignment/inbox_round_robin_service.rb` → line 40; `grep -n 'sort == queue.map(&:to_i).sort' app/services/auto_assignment/inbox_round_robin_service.rb` → line 53; direct test `spec/services/auto_assignment/inbox_round_robin_service_spec.rb`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-chatwoot", query: "InboxRoundRobinService available_agent queue reset", limit: 5 });
```
Rank-1: `InboxRoundRobinService.available_agent ...inbox_round_robin_service.rb 29-33`; `queue` 56-58 rank-2.

## Verdict
Adopt lazy self-healing via set-equality check + rotate-by-reinsert (pop then push-to-front of the PICKED agent), and keep eligibility filtering outside the rotation store. Adapt Redis list ops to any ordered store; keep string/integer normalization explicit at the boundary (the `.map(&:to_i)` on read is load-bearing against Redis strings). Omit per-inbox keying only if you have no tenant scoping.

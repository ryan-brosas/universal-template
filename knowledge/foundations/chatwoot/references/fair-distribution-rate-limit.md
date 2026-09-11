<!-- capsule-v2 -->
# Fair distribution rate limit — how is per-agent assignment volume capped within a sliding window?

**Source:** Chatwoot MIT `develop@6154aebcfea1fe62e8dd01fbf94568ef827fc51c`; Codebase Memory `ext-chatwoot`. **Question:** How do you stop round-robin from dumping unlimited conversations on one agent when they're the only online member?

## Redis key-per-assignment counting
**Path/Symbol:** `app/services/auto_assignment/rate_limiter.rb:AutoAssignment::RateLimiter` (whole file, 39 lines); config source `app/models/assignment_policy.rb` columns `fair_distribution_limit (default 100)` / `fair_distribution_window (default 3600s)`.
**Signature:** `within_limit? -> bool`; `track_assignment(conversation)`; `current_count -> int` via `Redis::Alfred.keys_count(pattern)`.
**Data Shape:** one Redis key per `(inbox_id, agent_id, conversation_id)` with `ex: window`; pattern-scoped KEYS-count as the counter.

### Decisive source
```ruby
def within_limit?
  current_count < limit
end

def track_assignment(conversation)
  assignment_key = build_assignment_key(conversation.id)
  Redis::Alfred.set(assignment_key, conversation.id.to_s, ex: window)
end

def current_count
  pattern = assignment_key_pattern
  Redis::Alfred.keys_count(pattern)
end

def limit
  config&.fair_distribution_limit.present? ? config.fair_distribution_limit.to_i : 5
end
```

**Flow:** V2 bulk pass filters candidates: for each inbox member, a RateLimiter counts live assignment keys under the agent's pattern → agents at/over `fair_distribution_limit` are dropped from this pass's pool (`filter_agents_by_rate_limit`) → after a successful claim, `track_assignment` writes the per-conversation key which EXPIRES after `fair_distribution_window` seconds, making the count a sliding window automatically. Policy row is optional: absent config falls back to limit **100** from the DB column default, but the in-code fallback when config is nil-present-blank differs (**5**) — a trap for porters who assume one constant.
**Invariant:** The counter granularity is PER-CONVERSATION keys, not an incrementing integer: expiry of individual keys yields a true rolling window with no background sweeper; idempotent re-tracking overwrites rather than double-counts. The gate runs BEFORE selection, so a saturated pool returns nil and the conversation stays unassigned until window slide.
**Probe:** `grep -n 'Redis::Alfred.keys_count(pattern)' app/services/auto_assignment/rate_limiter.rb` → line 15; direct test `spec/services/auto_assignment/rate_limiter_spec.rb`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-chatwoot", query: "RateLimiter within_limit fair_distribution track_assignment", limit: 5 });
```
Resolves `AutoAssignment::RateLimiter` methods line-exact in `app/services/auto_assignment/rate_limiter.rb`.

## Verdict
Adopt key-per-event-with-TTL counting for sliding-window caps where write rate is modest and exactness isn't critical. Adapt to token-bucket or sorted-set windows at higher scale; keep policy defaults co-located with DB column defaults and reconcile them deliberately. Omit Chatwoot's AssignmentPolicy join tables if your tenancy model stores policy inline.

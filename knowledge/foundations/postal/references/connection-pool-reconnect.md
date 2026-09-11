<!-- capsule-v2 -->
# Connection pool reconnect — how should a raw DB connection pool survive "MySQL server has gone away"?

**Source:** postal MIT `main@d038eaa8c763d3cafa797ccd6f773d53470bd336`; Codebase Memory `ext-postal`. **Question:** Which errors mean "the socket is dead" and how does the pool retry without leaking or poisoning connections?

## Postal::MessageDB::ConnectionPool
**Path/Symbol:** `lib/postal/message_db/connection_pool.rb:ConnectionPool` (use :14–39, checkout :43–49, checkin :52–56, add_new_connection :58–62, establish_connection :64–71).
**Signature:** `use { |connection| … } → block value (raises through)`.
**Data Shape:** `@connections = []` LIFO stack + `@lock = Mutex`; connections are raw `Mysql2::Client`s (no health-check on checkout).

### Decisive source
```ruby
def use
  retried = false
  do_not_checkin = false
  begin
    connection = checkout
    yield connection
  rescue Mysql2::Error => e
    if e.message =~ /(lost connection|gone away|not connected)/i
      do_not_checkin = true          # dead socket: NEVER return it to the pool
      if retried == false            # retry the WHOLE block exactly once…
        retried = true               # …on a FRESH connection (checkout re-runs)
        retry
      end
    end
    raise
  ensure
    checkin(connection) unless do_not_checkin   # healthy sockets always check in, even on error
  end
end
```

**Flow:** `use` checks a pooled client out (or dials a new one and retries the checkout) → yields → checks it back in under the mutex. A connectivity-flavored `Mysql2::Error` marks the socket unreturnable, flips `retried`, and `retry` re-enters the begin block so `checkout` dials fresh; a SECOND connectivity failure (or any other error class) propagates to the caller. Non-connectivity errors leave the connection presumed healthy — checked back in for reuse.
**Invariant:** classification is by MESSAGE REGEX (`lost connection|gone away|not connected`) because Mysql2 surfaces server death as generic `Mysql2::Error`; the ensure-block asymmetry is the point — dead connections are quarantined while error-but-alive ones are reused. Exactly one retry bounds latency; callers see the original exception afterward. The mutex covers only push/pop — queries run OUTSIDE the lock, so one slow query never blocks other threads.
**Probe:** `spec/lib/postal/message_db/connection_pool_spec.rb:8–51` (yields a client; checks in after success; checks in when the block raises StandardError; does NOT check in on "lost connection"; second client seen on retry — `clients_seen.uniq.size == 2`). Deterministic probe executed this pass re-derived quarantine + single-retry semantics.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-postal", query: "MessageDB ConnectionPool use checkout checkin", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt regex-classified dead-socket quarantine with a single full-block retry on a fresh connection, check-in-on-error for healthy sockets, and lock-only-around-stack discipline. Adapt the error matcher to your driver's error codes (prefer code-based matching where available). Omit nothing else — the pool is deliberately minimal.

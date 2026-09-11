<!-- capsule-v2 -->
# Live stats minute window — how do you keep cheap real-time counters without a time-series store?

**Source:** postal MIT `main@d038eaa8c763d3cafa797ccd6f773d53470bd336`; Codebase Memory `ext-postal`. **Question:** How does one small table answer "messages in the last N minutes" for every server without aggregation jobs?

## Postal::MessageDB::LiveStats
**Path/Symbol:** `lib/postal/message_db/live_stats.rb:increment` (14–20), `.total` (26–38); caller `app/lib/message_dequeuer/base.rb:increment_live_stats`.
**Signature:** `increment(type) → void` (type ∈ incoming/outgoing per scope); `total(minutes, types: [:incoming, :outgoing]) → Integer`.
**Data Shape:** `live_stats(type, minute, timestamp, count)` with UNIQUE `(type, minute)`; rows keyed to the wall-clock minute, refreshed in place.

### Decisive source
```ruby
def increment(type)
  time = Time.now.utc
  type = @database.escape(type.to_s)
  sql_query = "INSERT INTO …live_stats (type, minute, timestamp, count)"
  sql_query << " VALUES (#{type}, #{time.min}, #{time.to_f}, 1)"     # minute = time.min (0–59)…
  sql_query << " ON DUPLICATE KEY UPDATE"                            # …so the row rolls over hourly
  sql_query << " count = if(timestamp < #{time.to_f - 1800}, 1, count + 1), timestamp = #{time.to_f}"
end

def total(minutes, options = {})
  if minutes > 60 then raise Postal::Error, "Live stats can only return data for the last 60 minutes."
  options[:types] ||= [:incoming, :outgoing]
  raise Postal::Error, "You must provide at least one type to return" if options[:types].empty?
  result = @database.query("SELECT SUM(count) as count FROM … WHERE type IN (…) AND timestamp > #{
    minutes.minutes.ago.beginning_of_minute.utc.to_f}").first
  result["count"] || 0
end
```

**Flow:** every dequeued message bumps its scope's counter via a single upsert; the UNIQUE `(type, minute)` key makes same-minute increments collide into `count + 1`, and the timestamp guard RESETS to 1 when the last touch is older than 30 minutes — self-healing after idle gaps or clock jumps without any cleanup job. Reads SUM over a trailing window bounded by `beginning_of_minute` so partial current-minute data still counts.
**Invariant:** the 30-minute staleness threshold is what makes hour-boundary reuse of `time.min` safe: by the time minute-of-hour collides again (60 min later) the row is guaranteed stale and resets. Reads are capped at 60 minutes BY CONTRACT (larger windows belong to the Statistics plane's daily tables) and require ≥1 type — an empty type list would silently sum nothing.
**Probe:** no dedicated upstream spec for LiveStats; deterministic probe executed this pass re-derived both branches (`now−60s ⇒ +1`, `now−1900s ⇒ reset to 1`) and the read cap. Source-grounded caveat recorded; port with your own upsert test.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-postal", query: "LiveStats increment total", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt the single-upsert rolling minute counter with staleness-based reset and contract-capped reads when you need near-real-time throughput numbers from plain SQL. Adapt the window constants and key granularity (per-tenant column vs per-row type). Omit MySQL `ON DUPLICATE KEY` syntax if your DB needs `ON CONFLICT`.

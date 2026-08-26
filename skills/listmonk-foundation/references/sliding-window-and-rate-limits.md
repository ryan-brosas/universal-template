<!-- capsule-v2 -->
# sliding-window-and-rate-limits — How do the three send-rate limiters differ and where does each sleep?

**Source:** listmonk AGPL-3.0 `master@670c0171`; Codebase Memory `ext-listmonk`. **Question:** Which component enforces which throughput limit, and what state does each hold?

## Worker tick / pipe window / per-minute gauge
**Path/Symbol:** worker counter `internal/manager/manager.go:worker` (:489-573, rate check :508-511); global sliding window `internal/manager/pipe.go:NextSubscribers` (:81-141, check :113-137); per-pipe gauge `pipe.rate *ratecounter.RateCounter` (1-minute window) read by `GetCampaignStats` (`manager.go:338-347`).
**Signature:** `if numMsg >= m.cfg.MessageRate { time.Sleep(time.Second); numMsg = 0 }`; `p.m.slidingCount >= p.m.cfg.SlidingWindowRate → time.Sleep(windowDuration - diff)`.
**Data Shape:** SlidingWindow active only when `SlidingWindow && SlidingWindowRate > 0 && SlidingWindowDuration.Seconds() > 1`.

### Decisive source
```go
// pipe.go — GLOBAL window across ALL campaigns (state on Manager):
diff := time.Since(p.m.slidingStart)
if diff >= p.m.cfg.SlidingWindowDuration {
	p.m.slidingStart = time.Now()
	p.m.slidingCount = 0
}
p.m.slidingCount++
if p.m.slidingCount >= p.m.cfg.SlidingWindowRate {
	wait := p.m.cfg.SlidingWindowDuration - diff
	...
	time.Sleep(wait)
}
```

**Flow:** worker-level: each worker pauses 1s after sending its own `MessageRate` messages (per-worker multiplier ⇒ total ≈ Concurrency × MessageRate/sec). Pipe-level: while RENDERING a batch, after every queued message check the shared window; expiry resets count+clock; hitting the cap sleeps out the REMAINDER of the window on the producer side — backpressure lands in NextSubscribers, not in workers, so already-queued messages keep flowing. Stats: `rate.Incr(1)` per successful send feeds the 60s RateCounter surfaced as SendRate.
**Invariant:** The window is Manager-global, NOT per-campaign: two campaigns rendering concurrently share one budget and one clock; porters who move it onto the pipe multiply the cap by concurrent campaigns. The sleep happens while holding no locks but DOES block that campaign's batch loop by design.
**Probe:** `bash -c "cd <repo> && grep -c 'p.m.slidingCount >= p.m.cfg.SlidingWindowRate' internal/manager/pipe.go"` → 1; `grep -cF 'time.Sleep(time.Second)' internal/manager/manager.go` → 1.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-listmonk", query: "sliding window message rate", limit: 10 });
```
## Verdict
Adopt the producer-side remainder-sleep pattern for cross-job shared budgets. Adapt thresholds to your MTA's limits. Omit smtppool internals.

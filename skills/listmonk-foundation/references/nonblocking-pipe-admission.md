<!-- capsule-v2 -->
# nonblocking-pipe-admission — Why does enqueueing a campaign pipe never block, and what happens to a rejected pipe?

**Source:** listmonk AGPL-3.0 `master@670c0171`; Codebase Memory `ext-listmonk`. **Question:** What is the admission policy when the pipe channel is full, and why is blocking forbidden?

## Try-enqueue or release-immediately
**Path/Symbol:** `internal/manager/manager.go:Run` (:281-330), `scanCampaigns` (:449-487), `PushMessage`/`PushCampaignMessage` (:209-236).
**Signature:** `for p := range m.nextPipes { has, err := p.NextSubscribers(); ... select { case m.nextPipes <- p: default: p.Stop(false); p.wg.Done() } }`.
**Data Shape:** `nextPipes chan *pipe` buffered 1000; `campMsgQ`/`msgQ` buffered `Concurrency*MessageRate*2`.

### Decisive source
```go
select {
case m.nextPipes <- p:
default:
	// If the queue is full for any reason, stop the pipe and release it.
	// The cleanup() records the state in DB and scanCampaigns() picks it up
	// at a later point.
	p.Stop(false)
	p.wg.Done()
}
```

**Flow:** three distinct enqueue sites share the policy: scanCampaigns admitting NEW pipes, Run() requeueing pipes that still have subscribers, and the identical fallback in both. Rejection ⇒ immediately Stop(false) + release the sentinel wg slot so cleanup runs (deleting the pipe from the map) — the NEXT scan tick rediscovers the campaign fresh. Contrast PushMessage/PushCampaignMessage (transactional/one-off messages): those BLOCK up to `pushTimeout = 3s` on a ticker and fail loudly, because a dropped transactional email is lost forever while a dropped campaign tick is retried naturally.
**Invariant:** A blocked scan goroutine would freeze ALL campaigns behind one slow pipe AND go stale relative to DB state changes ("Blocking and waiting can end up in a race condition where the waiting campaign's state in the data source has changed" — upstream comment). Rejected-but-alive pipes must release their sentinel or the pipe map leaks.
**Probe:** `bash -c "cd <repo> && grep -c 'case m.nextPipes <- p:' internal/manager/manager.go"` → 2 (both try-enqueue sites carry the same default arm); `grep -nF 'pushTimeout = time.Second * 3' internal/manager/manager.go`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-listmonk", query: "scanCampaigns nextPipes", limit: 10 });
```
## Verdict
Adopt try-enqueue-with-release for retryable work admission; reserve bounded-blocking queues for unretryable per-item payloads. Adapt channel semantics to any MQ with immediate-negative-acknowledge. Omit the specific buffer arithmetic.

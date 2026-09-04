<!-- capsule-v2 -->
# pipe-waitgroup-completion — How does a campaign pipe know it is truly finished when messages are still queued?

**Source:** listmonk AGPL-3.0 `master@670c0171`; Codebase Memory `ext-listmonk`. **Question:** What coordinates stop/pause/error signals with in-flight messages so cleanup runs exactly once?

## Sentinel WaitGroup drain protocol
**Path/Symbol:** `internal/manager/pipe.go:newPipe` (:27-75), `newMessage` (:177-190), `worker` campMsgQ arm (`manager.go:489-573`), `OnError` (:143-160), `cleanup` (:192-244).
**Signature:** `func (m *Manager) newPipe(c *models.Campaign) (*pipe, error)`; pipe fields `wg sync.WaitGroup; sent atomic.Int64; lastID atomic.Uint64; errors atomic.Uint64; stopped atomic.Bool; withErrors atomic.Bool`.
**Data Shape:** wg starts at +1 (pseudo-message sentinel); each rendered message adds 1 via newMessage.

### Decisive source
```go
// newPipe: block Wait() immediately so cleanup fires only after real messages drain
p.wg.Add(1)
go func() { p.wg.Wait(); p.cleanup() }()
...
// worker: stopped pipes drop queued messages but MUST release their wg slot
if msg.pipe != nil && msg.pipe.stopped.Load() {
	msg.pipe.wg.Done()
	continue
}
...
// OnError: pause campaign when error threshold met
count := p.errors.Add(1)
if int(count) < p.m.cfg.MaxSendErrors { return }
p.Stop(true)
```

**Flow:** scan → newPipe compiles template/media then registers pipe → Run() loop calls NextSubscribers repeatedly (requeueing the pipe while more batches exist) → each message renders (render failure logs+skips WITHOUT wg increment — nothing was queued) → worker pops, checks stopped flag first → Push to messenger → wg.Done() then either OnError() (threshold ⇒ Stop(true)) or advance lastID/rate/sent → when queue empties and all messages done, sentinel releases → cleanup: flush counts (`UpdateCampaignCounts(id, 0, sent, lastID)`), then branch: withErrors ⇒ DB status paused + admin notification; stopped ⇒ just log; else refetch status from DB — only still-running/scheduled campaigns become finished.
**Invariant:** EVERY queued message must hit exactly one wg.Done() — the stopped-drop path, success path, and push-error path all converge there; missing one hangs the pipe forever (cleanup never fires). Cleanup's final status decision re-reads the DB rather than trusting local flags because a manual cancel may have landed mid-drain.
**Probe:** `bash -c "cd <repo> && grep -c 'p.wg.Add(1)' internal/manager/pipe.go"` → 2 (sentinel + per-message); `grep -cF 'models.CampaignStatusFinished' internal/manager/pipe.go` → 2; `grep -cF 'msg.pipe.wg.Done()' internal/manager/manager.go` → 1 (stopped-drop arm).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-listmonk", query: "pipe cleanup campaign finished", limit: 10 });
```
## Verdict
Adopt sentinel-WaitGroup drain semantics for any producer/consumer batch job with cooperative cancellation. Adapt atomics to your language's equivalents; keep "stop = mark, drain, cleanup-once". Omit the ratecounter dependency (any sliding window works).

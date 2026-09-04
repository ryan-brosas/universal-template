<!-- capsule-v2 -->
# Capture-rate sampling dice + offline timestamp rule — how does the server decide a session is recorded and when its clock starts?

**Source:** openreplay AGPL-3.0 (tracker MIT) `main@99eb600`; Codebase Memory `openreplay`. **Question:** Where exactly do sampling, bufferDiff backdating and offline mode alter the recorded start timestamp?

## rand(100) vs SampleRate; BufferDiff subtracted only under 5 min
**Path/Symbol:** `backend/pkg/sessions/api/web/handlers.go` — dice (:173–187: `byte(rand.Intn(100))`, condition-rate override), `getSessionTimestamp` (:74–83), flake-ID compose (:189–201); request flags `model.go` (`DoNotRecord`, `BufferDiff`, `IsOffline`, `Condition`).
**Signature:** `getSessionTimestamp(req *StartSessionRequest, startTimeMili int64) uint64`.
**Data Shape:** `dice >= SampleRate ⇒ 403 capture rate miss`; `BufferDiff` in ms accepted only `0 < diff < 5*60*1000`; offline trusts client ts outright.

### Decisive source
```go
func getSessionTimestamp(req *StartSessionRequest, startTimeMili int64) uint64 {
    if req.IsOffline { return uint64(req.Timestamp) }
    ts := uint64(startTimeMili)
    if req.BufferDiff > 0 && req.BufferDiff < 5*60*1000 { ts -= req.BufferDiff }
    return ts
}
```
```go
dice := byte(rand.Intn(100))
if req.Condition != "" { p.SampleRate = byte(rate) }  // per-condition override
if dice >= p.SampleRate { 403 "capture rate miss" }
```

**Flow:** new session (no/invalid token or Reset) → optional condition rate lookup replaces project sample rate → dice gate → sessionID = flake of server ms → recorded start = server now minus trusted cold-start buffer (bounded) → SessionStart row + Kafka message only when `recordSession(req)` (`!DoNotRecord`). Continuing sessions skip the whole block.
**Invariant:** Backdating is capped at 5 minutes — a hostile client can't pre-date a session arbitrarily; offline is an explicit opt-in flag, not inferred from BufferDiff magnitude.
**Probe:** `grep -c 'capture rate miss' backend/pkg/sessions/api/web/handlers.go` → `1`; `grep -cF '5*60*1000' backend/pkg/sessions/api/web/handlers.go` → `1`; `grep -c 'IsOffline' backend/pkg/sessions/api/web/handlers.go` → `1`.
**Coverage:** clean.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openreplay", query: "getSessionTimestamp BufferDiff SampleRate dice flaker", limit: 10 });
```

## Verdict
Adopt bounded backdate + explicit offline flag. Adapt sampling to your experiment framework. Omit condition rates if unused.

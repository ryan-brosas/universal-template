<!-- capsule-v2 -->
# BeaconCache TTL refresh — how is the per-session upload cap stored so hot sessions stay hot?

**Source:** openreplay AGPL-3.0 (tracker MIT) `main@99eb600`; Codebase Memory `openreplay`. **Question:** What caching pattern bounds memory for per-session beacon limits while keeping active sessions' limits fresh?

## Read-touches-TTL map with 2 min sweeper / 3 min expiry
**Path/Symbol:** `backend/pkg/sessions/api/beacon-cache.go` — `BeaconCache` (:13–17), `Add` (size≤0 rejected, :29–39), `Get` touch-on-read (:41–49), `cleaner` goroutine 2 min tick / 3 min max age (:51–63).
**Signature:** `Add(sessionID uint64, size int64)`; `Get(sessionID uint64) int64` → falls back to `defaultLimit`.
**Data Shape:** value struct `{size int64; time time.Time}` under RWMutex; keys are flake session ids.

### Decisive source
```go
func (e *BeaconCache) Get(sessionID uint64) int64 {
    e.mutex.RLock(); defer e.mutex.RUnlock()
    if beaconSize, ok := e.beaconSizeCache[sessionID]; ok {
        beaconSize.time = time.Now()   // read refreshes LRU-ish freshness
        return beaconSize.size
    }
    return e.defaultLimit
}
```

**Flow:** start-session stores project BeaconSize per session id → every ingest reads it to bound body size → a background goroutine deletes entries idle >3 min (checked every 2). Missing key ⇒ config default limit.
**Invariant:** Get must WRITE time under RLock — the entry struct is mutable shared state by design; porters copying to sync.Map must preserve the touch semantics or hot sessions get evicted mid-upload. Add rejects non-positive sizes so a misconfigured project can't zero-out caps.
**Probe:** `grep -c 'beaconSize.time = time.Now()' backend/pkg/sessions/api/beacon-cache.go` → `1`; `grep -c 'time.Minute\*3' backend/pkg/sessions/api/beacon-cache.go` → `1`; `grep -c 'time.Minute \* 2' backend/pkg/sessions/api/beacon-cache.go` → `1`.
**Coverage:** clean.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openreplay", query: "BeaconCache Add Get cleaner defaultLimit", limit: 10 });
```

## Verdict
Adopt touch-on-read + sweeper. Adapt limits/interval. Omit if your queue enforces caps upstream.

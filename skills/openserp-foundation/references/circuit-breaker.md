<!-- capsule-v2 -->
# Circuit breaker — what FSM isolates a failing engine, and how does fastest-mode read it?

**Source:** OpenSERP MIT `main@29c7b0fb`; Codebase Memory `ext-aeo-openserp`. **Question:** Which transitions gate traffic per engine, and why does half-open need TWO successes?

## Closed/Open/HalfOpen
**Path/Symbol:** `core/circuit_breaker.go` (whole file incl. CircuitBreakerManager), consumed in resilient.go AllowRequest/AvgSuccessLatency and mega fast mode (resilient.go L372–426).
**Signature:** `AllowRequest(ctx) bool`; `RecordSuccessDuration(ctx, elapsed)`; `RecordFailure(ctx)`; `AvgSuccessLatency() (time.Duration, bool)`; `Stats() map[string]any`.
**Data Shape:** defaults FailureThreshold 5, RecoveryTimeout 60s, SuccessThreshold 2; Stats expose state, failure_count, retry_in (ceil seconds, only when open), avg_response_ms.

### Decisive source
```go
case CircuitHalfOpen:
	cb.successCount++
	if cb.successCount >= cb.config.SuccessThreshold { cb.setState(CircuitClosed); reset counts }
case CircuitClosed:
	cb.failureCount++                       // success RESETS the streak
	if cb.failureCount >= cb.config.FailureThreshold { cb.setState(CircuitOpen) ... }
case CircuitHalfOpen: // failure path
	cb.setState(CircuitOpen); cb.successCount = 0    // re-open immediately
// open gate:
case CircuitOpen:
	if time.Since(cb.lastFailureTime) >= cb.config.RecoveryTimeout {
		cb.setState(CircuitHalfOpen); return true }
	return false
```

**Flow:** manager lazily creates one breaker per engine name; searchWithProtection consults AllowRequest before any work and records failure/success after; shouldRecordCircuitFailure excludes ctx-done and proxy-unavailable errors. Mega `fast` mode picks the candidate engine with lowest AvgSuccessLatency among circuit-closed engines (fallback candidates[0] when no samples yet).
**Invariant:** consecutive-failure semantics — any success in closed resets failureCount to 0; half-open admits requests but a single failure snaps straight back to open; health endpoint marks engine status "circuit_open" and overall degraded/unhealthy WITHOUT failing readiness (orchestrators shouldn't restart for a transient block).
**Probe:** `go test ./core -run 'TestCircuit'` (circuit_breaker_test.go covers threshold/recovery/half-open flaps).
**Probe executed (real runner):** same command at pin = **6 PASS** (opens-after-threshold, recovery-to-half-open, half-open success-closes, half-open failure-reopens, stats, manager all-stats) — the FSM table above is now backed by the repo's own suite, not just the Python re-derivation.
**Python-equivalent probe (executed):**
```python
state,fail,succ='closed',0,0
def record(ok):
    global state,fail,succ
    if ok:
        if state=='half-open':
            succ+=1
            if succ>=2: state,fail,succ='closed',0,0
        elif state=='closed': fail=0
    else:
        if state=='closed':
            fail+=1
            if fail>=5: state='open'
        elif state=='half-open': state,succ='open',0
for _ in range(5): record(False)
assert state=='open'
record(True); assert state=='open'          # still open until recovery elapses
state='half-open'; succ=0; record(True); record(True); assert state=='closed'
print("CB FSM GREEN: 5 fails→open; half-open needs 2 successes→closed")
```

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-openserp", query: "CircuitBreaker AllowRequest RecordFailure AvgSuccessLatency CircuitBreakerManager", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt the FSM constants and the latency-based fastest selection; adapt thresholds to your traffic; omit retry_in if your dashboard renders raw timestamps.

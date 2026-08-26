<!-- capsule-v2 -->
# Proxy registry & quarantine — how does rotation avoid dead IPs without bricking an exhausted pool?

**Source:** OpenSERP MIT `main@29c7b0fb`; Codebase Memory `ext-aeo-openserp`. **Question:** What is the difference between a FAILED, CHALLENGED, and QUARANTINED proxy, and how does a fully-exhausted tag recover?

## Registry state machine
**Path/Symbol:** `core/proxy.go:NextByTagWithContext/ReportFailure/ReportSuccess/ReportChallenged/startTagQuarantineLocked/leastFailedLocked` (L379–639).
**Signature:** `NextByTagWithContext(ctx, tag) string`; `HealthyCountForTag(tag) int` (challenged still counts); `ReportChallenged(ctx, url)`.
**Data Shape:** constants FailureThreshold 3, ProxyChallengeCooldown 2m, ProxyPoolQuarantineDuration 5m.

### Decisive source
```go
// two-pass rotation: first skip challenged, then relax so a challenged-but-only
// proxy is served rather than failing the request:
for _, skipChallenged := range []bool{true, false} {
	for i := 0; i < len(urls); i++ {
		idx := (start + i) % len(urls)
		state := r.states[urls[idx]]
		if state.disabled { continue }
		if skipChallenged && now.Before(state.challengedUntil) { continue }
		r.nextByTag[tag] = (idx+1)%len(urls); return urls[idx]
	}
}
// all disabled ⇒ quarantine (refuse to serve), then PROBE recovery:
if r.allDisabledLocked(urls) {
	if quarantineUntil.IsZero() { startTagQuarantineLocked(...); return "" }
	if now.Before(quarantineUntil) { return "" }
	delete(r.tagQuarantine, tag)
	probe := r.leastFailedLocked(urls)     // cheapest probe candidate
	state.disabled = false; state.failures = 0
}
// success clears quarantine for every shared tag:
state.failures = 0; state.disabled = false
for _, tag := range state.tags { delete(r.tagQuarantine, tag) }
```

**Flow:** ReportFailure increments; at threshold disables the proxy AND starts quarantine for any tag whose pool just went fully disabled. ReportSuccess resets failures, re-enables, clears quarantine. ReportChallenged only sets challengedUntil = now+2m (never disables, never quarantines) — IP reputation problem, not a dead IP.
**Invariant:** only IsProxyNetworkError-classified failures reach ReportFailure (callers must not degrade health for captchas); HealthyCountForTag counts disabled=false regardless of challenge so rotation gating (≥2) works while a peer is merely cooling down.
**Probe:** `go test ./core -run TestProxyRotation` — pins: challenged deprioritized WITHOUT disabling; captcha rotates once with 2 proxies; single-proxy fails fast; global challenge reports no rotation; direct fails fast.
**Probe executed (real runner):** the literal `-run TestProxyRotation` matches ZERO tests (rotation coverage lives in named tests across files); repaired: `go test ./core -run 'TestSearchWithProtection_RotatesProxyOnCaptcha|TestPoolQuarantine|TestReportChallenged'` = **5 PASS** at pin — every pinned rotation/quarantine behavior executed green (plus TestReportSuccess/ReportFailure/TestPoolQuarantineAfterExhaustion in the same green package run).
**Python-equivalent probe (executed):**
```python
import time
class P:
    def __init__(s): s.disabled=False; s.fail=0; s.chal=0
reg={'p1':P(),'p2':P()}; nxt=0
def next_by_tag():
    global nxt
    now=time.time()
    for skip in (True,False):
        for i in range(2):
            idx=(nxt+i)%2; k=f'p{idx+1}'; st=reg[k]
            if st.disabled: continue
            if skip and now<st.chal: continue
            nxt=(idx+1)%2; return k
    return None
k1=next_by_tag(); reg[k1].chal=time.time()+120   # challenged cooldown
k2=next_by_tag()
assert k1!=k2 and k2 not in (None,), (k1,k2)
print("two-pass rotation GREEN:", k1,"challenged →",k2,"served")
```

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-openserp", query: "ProxyRegistry NextByTagWithContext ReportChallenged tagQuarantine leastFailedLocked", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt failed/challenged/quarantined as three distinct states with distinct timers; adapt thresholds/cooldowns to your provider SLAs; omit multi-tag sharing if each proxy has exactly one purpose.

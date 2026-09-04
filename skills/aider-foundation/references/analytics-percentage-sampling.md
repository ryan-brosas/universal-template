<!-- capsule-v2 -->
# Analytics percentage sampling — first-6-hex UUID threshold with opt-in persistence

**Source:** Aider Apache-2.0 `main@5dc9490bb35f9729ef2c95d00a19ccd30c26339c`; Codebase Memory project `aider`. **Question:** How do you sample telemetry deterministically per install (same user always in or out) and keep the opt-out absolutely permanent?

## Compare the user-id's first 6 hex digits against a percent-derived ceiling; persist every consent decision to disk
**Path/Symbol:** `aider/analytics.py`: `PERCENT = 10` (:8), `compute_hex_threshold(percent)` (:18), `is_uuid_in_percentage(uuid_str, percent)` (:31), `Analytics.__init__(logfile, permanently_disable, posthog_host, posthog_project_api_key)` (:63), opt-in ask block `main.py` :642-662, persistence via `~/.aider/analytics.json` (`save_data()`), `analytics.event("launched"/"exit", reason=...)`.
**Signature:** `threshold = format(int(0xFFFFFF * percent / 100), "06x")`; membership = `uuid_str[:6] <= threshold` (lexicographic on hex = numeric on the 24-bit prefix).
**Data Shape:** EXECUTED this run against live source: thresholds are 1%→`028f5c`, 10%→`199999`, 50%→`7fffff`; boundary semantics: `uuid[:6] == threshold` is IN (test_analytics.py :113 pins `'019990...' in 1%`? no — :112-113 pin `'01999...' True / '020000...' True` at 1%, i.e. ceiling inclusive); percent=0 and empty uuid both → False; percent outside [0,100] raises.

### Decisive source
```python
def is_uuid_in_percentage(uuid_str, percent):
    if not (0 <= percent <= 100):
        raise ValueError("Percentage must be between 0 and 100")
    if not uuid_str:
        return False
    if percent == 0:
        return False
    threshold = compute_hex_threshold(percent)
    return uuid_str[:6] <= threshold
```

**Flow:** launch → load saved `{user_id, asked_opt_in, permanently_disable}` → if unset, ask once with the privacy blurb, write the decision immediately (`disable(permanently=True)` writes a flag no later code path clears) → gate every `event()` on membership + enablement. main.py additionally emits structured exit reasons for EVERY early return ("Recursing with correct repo", "Invalid directory input", "Completed --message", ...).
**Invariant:** sampling is a pure function of a STABLE per-install uuid — never per-session random — so cohorts don't churn; permanent-disable is checked before provider construction so opted-out installs make zero network calls.
**Probe:** direct tests `tests/basic/test_analytics.py::test_is_uuid_in_percentage` (:107) + enable/disable/persistence suite (:27-82) executed GREEN this run via repo venv (`python -m pytest tests/basic/test_analytics.py -q`: **7 passed**). Deterministic: `grep -nF 'compute_hex_threshold' aider/analytics.py | head -2` → :18 def + :51 call.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "aider", query: "compute_hex_threshold", limit: 3 });
// rank-1: aider.aider.analytics.compute_hex_threshold aider/analytics.py 18-27
```

## Verdict
Adopt the deterministic hex-prefix sampler verbatim (10% default); adapt providers freely. The durable-never-re-ask invariant is the compliance-critical half — porters who re-prompt each run or sample per-session break both UX trust and cohort stability.

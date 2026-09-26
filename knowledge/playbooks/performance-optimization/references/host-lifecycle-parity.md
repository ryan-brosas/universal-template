# Validate host lifecycle parity before benchmarking

Use when a local benchmark calls production host methods through a partial
receiver or test double, or helper tests pass without exercising the runner.
Calling real code does not establish that the harness supplies its real lifecycle.

## Trace, reproduce, then measure

1. **Map the executable path and its coverage.** Trace runner → host receiver →
   deferred queue → flush event → outbound request. Read the loaded host's state
   prerequisites and scheduling behavior. Check whether the passing gates execute
   this entrypoint; a typecheck may exclude a JavaScript runner while its helper
   tests never invoke it.
2. **Probe the failing boundary with a control.** Invoke the actual host method
   using the runner's receiver and delivery options. Compare with a receiver that
   supplies the missing prerequisite. A queue-only control proves enqueue works,
   not that the message reaches a request. Follow the deferred message through
   its flush event and capture what the consumer receives before declaring parity.
3. **Reuse lifecycle behavior, not just field names.** When repair is authorized,
   prefer the real host or a validated fixture shared by the integration tests and
   benchmark. Preserve the relevant state, event subscriptions, flush timing and
   cleanup. A completed tool result is not necessarily a completed turn; placing
   the transcript at the wrong boundary can create a spurious wake-up request.
   Keep passive versus active delivery matched between candidate and control,
   unless that distinction is the variable under test. Do not copy an entire host
   or treat private-field initialization as a portable recipe. A minimal double
   remains valid for a narrower contract when its limits are explicit.
4. **Lock the runner and request contract.** Exercise the actual entrypoint in a
   small smoke test, including workers and output parsing where applicable. Inspect
   outbound requests at the transport/provider boundary, outside the timing window.
   Assert required first-request content, absence of stale content, and one canonical
   payload per relevant request. Eventual transcript presence can hide an empty first
   request; exactly-once content does not mean exactly one request overall. Legitimate
   steering turns may produce several. Derive request counts from the host contract
   and a witnessed control, not by relaxing expectations until the runner passes.
5. **Prove the check can fail.** Drop the required payload in a negative canary;
   the request assertion must reject it while the faithful control passes. Only
   then use the harness for its stated measurement layer.

## Boundaries

A findings-only request stops at reproduction and diagnosis, not fixture repair.
This sequence validates local lifecycle and request-shape claims. Stubbed provider
results cannot establish live latency, billed cost or output quality; use the
[controlled benchmark evidence layers](controlled-dogfood-benchmarks.md#separate-the-evidence-layers)
for those claims.

# Run controlled dogfood benchmarks

Use when a measurement must answer whether a candidate beats current behavior on
a real end-to-end pipeline (an agent, CLI, service or app) rather than a
synthetic microbenchmark. For recurring work across runtime boundaries, build the
[boundary budget](recurring-cross-boundary-work.md) first.
For repeated live reliability runs rather than a superiority comparison, use
[repeated live dogfood](repeated-live-dogfood.md) to freeze the protocol, resume
from receipts, and separate task, lifecycle, scope and coverage verdicts.

## Seed from live dogfood evidence

Start from a run that already exercised the production path: a dogfood session,
captured trace or recorded job. Reuse its inputs, configuration and revision so
the benchmark measures real behavior, and record where each number came from. Do
not invent a workload the product never runs. Mixed-revision or multi-model
history supplies workloads and hypotheses, not a matched control.

## Separate the evidence layers

1. Deterministic probes and regressions establish correctness, not speed or savings.
2. A local harness measures orchestration and request shape. Even when it invokes
   production code, stubbed providers cannot establish real latency or billed cost.
3. Matched end-to-end runs measure actual completion time, usage, cost and result
   quality. Use these before claiming a user-visible benefit.

Report which layers ran and which remain unmeasured. A fixed defect can increase
context or work; report that tradeoff without calling it a performance win.

## Validate host lifecycle parity

A local harness can call production methods yet omit the receiver state or deferred
flush that makes them work. Before trusting its timings, validate
[host lifecycle parity](host-lifecycle-parity.md), including the actual runner and
outbound requests rather than only helper tests.

## Account for the experiment and its spend

Freeze the task-by-arm matrix, each attempt's state, and the schedule as the
denominator for every rate and cost:
[benchmark outcome accounting](benchmark-outcome-accounting.md). When arms, models
or attempts share one spend limit, confirm the limit is checked at the request
boundary before calling it a cap:
[shared budget accounting](shared-budget-accounting.md).

## Run the production owner, matched

Invoke the same production owner, entrypoint and configuration on both sides.
Toggle only the variant under test; keep model, host, inputs, mounted consumers
and sampling window equal. Confirm the control reproduces current behavior before
trusting the canary. When several changes ride together, claim only their combined
effect unless separate runs attribute them.

## Repeat fresh-process workers with warmups

Let each worker warm up, then reset counters before the sampling window so
compile and cache state is not the measurement. Repeat the process per side
rather than reusing one long-lived process, and report per-worker medians with
their spread. Treat a difference smaller than the spread as unresolved, not a win.

## Keep units, costs and identity honest

- Label every number with its unit and what it measures. Context bytes are not
  tokens; token estimates are not billed cost; milliseconds are not microseconds.
- Keep per-worker values so a median can be recomputed instead of collapsing
  them into one aggregate.
- Score output quality the same way on both sides (same rubric, same judge,
  same sample), and report it beside latency and cost rather than trading one
  away silently.
- Preserve source revision, runner command, host and worker identity with the
  results. Without them, a later comparison measures a different system.

## Prioritize findings, protect the evidence

- Turn each suspected defect into a deterministic probe before ranking it;
  prioritize by impact and effort once the probe reproduces it.
- Archive raw output with a content hash before compression, then restore and
  compare that hash before deleting the source. A compressed archive is not yet
  evidence until the roundtrip is verified.
- Do not replay a run that already completed when a timeout or handoff moves the
  work elsewhere; continue from the recorded results.
- A measurement-only request authorizes measurement. Report an optimization or
  bug found while measuring as a finding, and leave its implementation for the
  request that asks for it ([code discipline](../../code-discipline/README.md)).

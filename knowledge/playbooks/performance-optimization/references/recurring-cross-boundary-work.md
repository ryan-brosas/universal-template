# Measure recurring work across UI boundaries

Use this when lag appears around timers, subscription hooks, streamed updates, or
calls into native, worker, process, plugin, or IPC runtimes, especially when only
one platform is affected.

## Build a boundary budget

Start with the recurring producer, not the component that looks busy:

```text
operations / second = instances × updates / second × operations / update
blocked time / second = operations / second × duration / operation
```

Enumerate every caller and expand wrappers far enough to expose hidden work. A
single hook can issue several boundary calls. Read the implementation for the
exact runtime revision and target platform, then classify each operation as
same-thread, queued asynchronous work, a blocking thread/IPC round trip, a
constant/no-op, or an event-backed value. For implementation outside the app,
follow [cross-repository source](../../cross-repo-source/README.md), re-read the
decisive source, and compare relevant working-tree differences. Do not infer one
platform's cost from another's path.

Instrument the lowest interceptable boundary. Count calls per second and, when
possible, their duration distribution. Render counts and timer counts are useful
navigation signals, not substitutes for measuring the expensive operation.

## Make the comparison faithful

Use the same target runtime, workload, mounted consumers, and sampling window for
baseline and candidate. Reproduce the real legacy topology when measuring a
historical baseline. Run the production owner or import its configuration instead
of retyping intervals and defaults in the probe; otherwise the benchmark can
measure a design the application never runs.

Separate mount/warm-up work from steady state. Let the tree settle, then reset
counters before the sampling window. Report both when startup matters. Label a
simulated historical baseline as such. If one comparison contains several
changes, claim only their combined effect unless separate runs attribute them.
When claiming a platform effect, either run the same workload on a control
platform or separate source-proven implementation differences from target-only
runtime measurements.

## Reduce the multiplying factor

Prefer the smallest owning-boundary change in this order:

1. **Ownership:** one lifecycle owner per scope observes each changing fact;
   consumers share its snapshot. Keep registration, timer, and cleanup together.
2. **Cadence:** poll at the slowest freshness the behavior permits. Do not keep
   querying a platform value proved constant. Inspect batching semantics: for a
   schedule-on-first trailing window, the delay must exceed the normal producer
   gap or it fires for nearly every update. A reset-on-update debounce can starve
   a continuous stream, so add a maximum wait when freshness requires one. Batch
   only coalescible intermediate state; flush authoritative transitions promptly.
3. **Scope:** compute only for active, visible, or expanded consumers. Move maps,
   filtering, and allocations into the narrowest consumer that needs them.
4. **Runtime architecture:** add an event or nonblocking snapshot only when the
   app-level fan-out is removed and source evidence shows the deeper change is
   still necessary.

Preserve legitimate standalone, embed, and test behavior. A one-time fallback
read can be acceptable even when a recurring fallback timer is not; measure the
difference rather than forcing one architecture everywhere.

## Verify the mechanism and the symptom

Re-run the same boundary probe and an end-to-end user metric such as input latency
or frame time. Test ownership, cadence, coalescing, lifecycle cleanup, and fallback
behavior. Sweep analogous timers and call sites after the edit, run correctness
gates, and smoke the affected platform. A skipped platform suite is an evidence
gap, not a pass.

Fewer measured calls prove lower call frequency. They prove less blocked time
only when per-call cost is also measured or shown unchanged; neither result by
itself proves that perceived lag was fixed. If the end-to-end metric does not
move, retain the bounded improvement only when it is worthwhile and continue
with CPU, GPU, rendering, I/O, or scheduling evidence. Do not trade required
freshness for a better counter.

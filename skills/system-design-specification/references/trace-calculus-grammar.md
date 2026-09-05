# Trace Calculus Grammar — ASCII Sequence Notation for Asynchronous State Machines

Use this optional notation when an event-history/WAL model benefits from compact
interleaving traces. Keep another notation if it already exposes the relevant
ordering, causality, and persistence boundaries.

## The Problem

Dense prose can hide interleavings and crash boundaries. A trace, sequence
diagram, state machine, or formal model can make them easier to inspect. The
notation alone does not establish exhaustive coverage.

## The 6-Letter Trace Notation

For this event-system example, six labels describe the relevant operations.
Extend or replace them when the model needs other events; do not treat vertical
layout as a global clock across independent processes:

```text
E   Entry / data node appended to shared persistent state (e.g. conversation DAG)
R   Record appended to local execution log / WAL (e.g. intent, attempt, queue)
L   Pointer move (e.g. lane/branch navigation)
G   Global fact / configuration written (latest-write-wins)
H   Hook / interceptor awaited
X   Crash site / fault injection point
```

## How to Write Trace Sequences

### 1. Simple Linear Execution
```text
    prompt("refactor auth")
H   before_run                        may inject entries, override system prompt
R   operation_started                 kind run; initial messages with provisioned ids
E   user message                      the provisioned id from the intent
R   step_attempt                      step assistant, attempt 1
E   assistant message [tool call]
H   before_tool                       may change args or block
R   tool_started                      effective args, provisioned result id, replay safety
H   after_tool                        may patch result and terminate
E   tool result                       the provisioned result id
R   step_attempt                      next turn's assistant step, attempt 1
E   assistant message "done"
R   operation_finished                completed
```

### 2. Concurrent Queueing & Interleaving
```text
E   assistant message [tool call]
R   tool_started
    steer("focus on the tests")       caller resolves here
R   queue_enqueued                    steer, full payload, provisioned id
E   tool result
E   user message                      checkpoint consumes the queue item
R   step_attempt                      next request sees the steering message
```

### 3. Competing Race Conditions
Show the two possible linearized outcomes side-by-side:
```text
Steer first                         Finish first
-----------                         ------------
R   queue_enqueued                  R   operation_finished
    tryFinishRun -> continue            steer() -> NoActiveRun
E   user message
... run continues
R   operation_finished
```

## Invariants for Trace Writing
1. **Vertical Order is Time Order**: Top to bottom represents process-local execution time.
2. **Horizontal Alignment Shows Boundaries**: Indent external caller events and show exactly where caller promises resolve.
3. **Every State Transition is Observable**: If a write happens in memory vs storage, differentiate it explicitly.

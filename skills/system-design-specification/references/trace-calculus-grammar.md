# Trace Calculus Grammar — ASCII Sequence Notation for Asynchronous State Machines

Use this reference when authoring architectural specifications for complex distributed, concurrent, or asynchronous systems.

## The Problem
Prose descriptions of async interleaved operations (e.g. "if the user steers while tool call 1 is running but tool call 2 has not started and abort is requested") are error-prone, ambiguous, and impossible to verify exhaustively.

## The 6-Letter Trace Notation
Every system event is classified into one of 6 primitive categories:

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

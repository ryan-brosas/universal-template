# Provisioned ID Protocols — Pre-allocated Intent for Crash-Proof Effects

Use this reference when designing systems that interact with external services, file system side effects, or asynchronous tool calls.

## The Problem
If you generate IDs only after an external effect completes:
```text
Effect completes -> Process crashes -> No ID on disk -> System restarts -> Re-runs effect -> Duplicate execution!
```

## The Solution: Intent Pre-allocation
Allocate the entry's UUID and log the intent record to storage **before** initiating the external effect:

```text
1. Pre-allocate ID: entryId = randomUUID()
2. Log Intent:      R  tool_started { toolCallId, entryId, effectiveArgs, replay: "never" }
3. Execute Effect:  result = await externalTool(args)
4. Commit Entry:    E  tool_result  { id: entryId, result }
```

## Recovery Invariants
When the system boots up:
1. It scans the operation log for `tool_started` records that have no matching `tool_result` entry in the DAG.
2. If `replay === "safe"`: it re-executes using the pre-allocated `entryId`.
3. If `replay === "never"`: it commits a synthetic `interrupted` result using the pre-allocated `entryId`.

## Resulting Guarantee
- **No orphan effects**: Every external action has a traceable ID stamped before it begins.
- **No distributed 2PC required**: Storage and external effects stay synchronized across sudden power loss or process kill (`kill -9`).

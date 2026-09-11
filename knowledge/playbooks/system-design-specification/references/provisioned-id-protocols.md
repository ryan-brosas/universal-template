# Provisioned IDs — Durable Intent, Not Exactly-Once Effects

Use this pattern when an event-history system needs a stable local result identity
across process death. Compare it with existing transaction, outbox, idempotency,
and reconciliation facilities before introducing a new log.

## The ambiguous-completion window

```text
Effect completes -> process crashes -> no local result -> recovery sees unknown outcome
```

Retrying blindly may duplicate the remote action. A preallocated result ID makes
the attempt identifiable but does not, by itself, close that window.

## Example intent-first protocol

```text
1. Pre-allocate ID: entryId = randomUUID()
2. Persist intent: R tool_started { toolCallId, entryId, effectiveArgs, replay: "never" }
3. Execute effect: result = await externalTool(effectiveArgs)
4. Commit result:  E tool_result { id: entryId, result }
```

The intent must be durable before execution **for this protocol's guarantee**.
Define atomic/unique result insertion and recovery ownership too; concurrent
recoverers must not independently commit or replay the same attempt.

## Recovery choices

- A result exists under the provisioned ID: do not append a duplicate result.
- No result exists and both persisted policy and the current effect contract permit
  replay: retry with the same identity and persisted effective arguments. A remote
  service must actually enforce an idempotency key if that is what makes retry safe;
  sending a local UUID is not sufficient.
- Replay is unsafe or completion is unknown: reconcile using remote evidence,
  stop for an authorized operator, or append a local `interrupted` outcome according
  to the project's contract. That outcome does not assert that the remote action
  failed or was undone. Compensation is a separate effect requiring its own policy.

## What this establishes

Durable intent links an attempted action to its local result/recovery record under
the stated storage assumptions. It does not synchronize remote and local commits,
provide distributed atomicity, or guarantee exactly-once execution. Bound any
stronger claim by the remote idempotency, retention, concurrency, and failure
contracts and verify those boundaries with fault-injection or integration tests.

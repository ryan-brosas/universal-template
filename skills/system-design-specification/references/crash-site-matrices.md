# Crash-Site Matrices — Recovery Within a Stated Failure Model

Use this reference when specifying multi-step asynchronous workflows, tool batches, database writes, or background job recovery.

## The Principle

Map each modeled fault boundary to the durable observations and permitted recovery
actions. A complete table supports a bounded recovery claim; it is not proof
against failures outside the storage, concurrency, or network assumptions.
Distinguish unknown external completion from a confirmed failure.

## Structuring the Crash Diagram

Identify process-death boundaries in the chosen workflow. This example assumes
`before_tool` is replay-safe and has no untracked external mutation. Hooks with
effects need their own intent/recovery contract and fault sites:

```text
E   assistant message, calls c1, c2
X1  before before_tool hook           nothing durable for c1
H   before_tool(c1)
X2  hook resolved, nothing written    same durable state as X1
R   tool_started(c1)
X3  tool executing
H   after_tool(c1)
X4  hook interrupted                  same durable state as X3
E   tool result c1
X5  result durable                    c1 finished; c2 at X1
```

## The Exhaustive Crash Matrix Format

| Crash Site | Durable State in Storage | Recovery Algorithm on Startup |
| :--- | :--- | :--- |
| **$X_1$, $X_2$** (before `tool_started`) | No record, no result entry | Re-run `before_tool` hook normally (idempotent). |
| **$X_3$, $X_4$** (`tool_started` logged, no result) | `tool_started` exists without matching result | If `record.replay === "safe"` AND `currentTool.replay === "safe"`:<br/>&nbsp;&nbsp;$\to$ Re-execute tool with persisted `effectiveArgs` under the project's retry/authorization contract.<br/>Else:<br/>&nbsp;&nbsp;$\to$ Outcome is **unknown**, not failed. Record the attempt as unresolved and require reconciliation against remote evidence, compensation under its own policy, or operator resolution before advancing; do not append a synthetic `"interrupted"` result that asserts remote failure. |
| **$X_5$** (result entry exists) | Result entry exists with provisioned ID | Skip $c_1$; proceed to $c_2$ at $X_1$. |

## Rules for Constructing Matrix Tables
1. **Name Every Boundary**: Label each crash site $X_1, X_2, \dots, X_n$ consecutively.
2. **Examine Storage, Not Memory**: The "Durable State" column must only describe what was actually flushed to disk/database before $X_n$.
3. **No Silent Assumptions**: Represent ambiguity explicitly. The recovery action
   may be reconciliation, compensation, or stopping for an operator; an intent
   record alone does not reveal whether a remote effect completed.
4. **Replay Safety is Explicit**: Assess the effect contract, including callbacks,
   billing, and external idempotency. Do not infer safe replay from a method name
   or assume a synthetic interrupted result means the remote effect did not run.

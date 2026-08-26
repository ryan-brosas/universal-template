# Crash-Site Matrices — Constructive Proofs for Crash-Proof Systems

Use this reference when specifying multi-step asynchronous workflows, tool batches, database writes, or background job recovery.

## The Principle
To prove that a system has **zero unhandled failure states**, never write generic prose like "if it fails, the system recovers." Instead, construct an exhaustive **Crash Matrix** mapping every single failure point $X_n$ between effects to the exact durable state on disk and the deterministic recovery algorithm.

## Structuring the Crash Diagram

Identify every transition where process death could occur:

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
| **$X_3$, $X_4$** (`tool_started` logged, no result) | `tool_started` exists without matching result | If `record.replay === "safe"` AND `currentTool.replay === "safe"`:<br/>&nbsp;&nbsp;$\to$ Re-execute tool with persisted `effectiveArgs`.<br/>Else:<br/>&nbsp;&nbsp;$\to$ Append synthetic `"interrupted"` result entry (never blindly re-run mutating effects). |
| **$X_5$** (result entry exists) | Result entry exists with provisioned ID | Skip $c_1$; proceed to $c_2$ at $X_1$. |

## Rules for Constructing Matrix Tables
1. **Name Every Boundary**: Label each crash site $X_1, X_2, \dots, X_n$ consecutively.
2. **Examine Storage, Not Memory**: The "Durable State" column must only describe what was actually flushed to disk/database before $X_n$.
3. **No Unhandled Rows**: If a row has ambiguity, your protocol is incomplete. Add an intent record or make the operation idempotent.
4. **Replay Safety is Explicit**: Differentiate read-only queries (`replay: safe`) from mutations (`replay: never`).

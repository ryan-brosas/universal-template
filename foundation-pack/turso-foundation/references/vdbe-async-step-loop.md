<!-- capsule-v2 -->
# VDBE async step loop — how does a bytecode VM yield on IO and resume without blocking its thread?

**Source:** turso (MIT) `main@def9a0601b8e` (/mnt/hdd/utopia/inspo/memory/turso); Codebase Memory project `turso`. **Question:** What does the VM return to the caller, what state survives across a resume, and which errors must NOT roll back?

## Step returns IO/Yield/Row/Done; instructions own their resume state
**Path/Symbol:** `core/vdbe/mod.rs`: `Program::step` (:1661-1683), `normal_step` (:1833-1999), `InsnFunctionStepResult::{Step, Done, IO, Row}`; `core/types.rs`: `IOResult<T> = Done(T) | IO(IOCompletions)` (:3453-3456) + `return_if_io!` macro (:3483-3494) + `return_and_restore_if_io!` (:3497+); per-op resume enums in `core/vdbe/execute.rs` (e.g. `OpSeekState` :5713-5723: Start → Seek{key,op} → Advance{op} → MoveLast).
**Signature:** `fn step(&self, state: &mut ProgramState, pager: &Arc<Pager>, query_mode, waker: Option<&Waker>) -> Result<StepResult>` — one call dispatches instructions until an IO boundary.
**Data Shape:** ProgramState carries `io_completions: Option<IOCompletions>` (the pending op slot), per-op state enums stored OUTSIDE the pc (the slot stays at the same opcode so the instruction re-executes into its saved sub-state), metrics counters, result_row handed out only between steps.

### Decisive source
```rust
// mod.rs:1848-1876 — completion check at loop top:
//   if !io.finished() { io.set_waker(waker); return Ok(StepResult::IO); }
//   if let Some(err) = io.get_error() {
//     if pager.is_checkpointing() {
//       // Wrap IO errors that occurred during checkpointing in
//       // CheckpointFailed … so that abort() knows not to try to rollback
//       // the transaction, because the transaction is already durable in
//       // the WAL and hence committed. (also lets the simulator shadow results)
// mod.rs:1951-1971 — Ok(InsnFunctionStepResult::IO(io)):
//   let is_yield = io.is_explicit_yield();
//   if is_yield { /* "yields aren't pending I/O, so the instruction will
//      simply re-execute on the next step" */ return Ok(StepResult::Yield); }
//   state.io_completions = Some(io);
//   if !finished { return Ok(StepResult::IO); }
//   continue 'io_check;  // already finished → observe errors, keep running
```

**Flow:** outer `'io_check` loop runs once per step call and re-enters when an instruction completed its IO inline; inner loop dispatches instructions without re-inspecting the completion slot every time. Busy → StepResult::Busy (retry same PC); BusySnapshot while no transaction → also Busy ("for auto-commits or BEGIN IMMEDIATE… auto-retrying can be useful"); any other Err → abort() then propagate. Connection-closed mid-write rolls back the tx before erroring.
**Invariant:** after ANY IO return the SAME instruction re-executes — every side-effecting opcode must be idempotent-under-replay or split so the mutating step happens exactly once (that is what the Op*State enums encode). Checkpoint-phase IO errors are classified BEFORE abort because rolling back an already-durable commit is forbidden.
**Probe:** `core/vdbe/statement_lifecycle_tests.rs:293-300` (`test_returning_owner_drop_does_not_commit_interrupted_drop_table`) and `:365-372` (`test_drop_table_while_returning_active_is_table_locked`) pin interrupted-DDL semantics over MemoryIO.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "normal_step InsnFunctionStepResult io_completions OpSeekState", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-channel step protocol (IO with stored completion / explicit cooperative Yield that stores nothing / Row-Done-Busy terminations) for any resumable VM over async storage. Adapt instruction set freely; do NOT adapt the "resume at same PC" rule or the checkpoint-error classification. Omit tracing/explain plumbing (explain_step is a parallel interpreter, not needed for correctness).

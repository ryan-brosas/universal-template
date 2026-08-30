<!-- capsule-v2 -->
# BTreeCursor count machine — how do you count a whole b-tree when every page read can asynchronously spill mid-descent without double counting?

**Source:** turso MIT `main@f1800bb8c` (re-anchored from `def9a060`); Codebase Memory `turso`. **Question:** A cursor method that mutates counters and descends pages in one loop body — where must each mutation sit so an IO yield between them cannot re-apply it on resume?

## CountState::Start → Loop → Descend → Finish with mutation-before-yield discipline
**Path/Symbol:** `core/storage/btree.rs:7045-7188` (`fn count(&mut self) -> Result<IOResult<usize>>` impl at :7007; trait decl :734), state enum `CountState` at `core/storage/state_machines.rs:34-46`, cursor slot `count_state` (`btree.rs:830`). Sibling per-method enums live in the same file: `EmptyTableState`, `MoveToRightState`, `SeekToLastState`, `RewindState`, `AdvanceState`, `SeekEndState`, `MoveToState`.
**Signature:** `fn count(&mut self) -> Result<IOResult<usize>>` — reentrant; callers drive it with a `run_until_done`-style loop that re-invokes on `IOResult::IO`.
**Data Shape:** `CountState::Descend { target: i64 }` is the ONLY payload-carrying variant: it stores the child page id whose `read_page` spilled, so resume retries exactly the read+advance+push, not the loop-top mutations.

### Decisive source
```rust
// btree.rs:7076-7090 — why Descend exists:
// Spill yield here would re-enter `CountState::Loop`,
// which re-runs `stack.advance()` and the leaf-count
// increment. Transition to `CountState::Descend` so
// re-entry skips those mutations and only retries the
// read + (second) advance + push.
// state_machines.rs:37-41 — same contract documented ON the enum variant:
/// Resume state used after `CountState::Loop` yielded for spill IO
/// mid-descent. The loop-top `stack.advance()` and `self.count +=
/// cell_count()` mutations have already been applied for this step ...
```
Two more load-bearing orderings: (1) exhaustion transitions to `Finish` BEFORE performing the finalizing `move_to_root_nonblock` (:7033-7036 "so a spill yield from it can't re-enter `Loop`'s `count += cell_count()`") — finalization IO must never re-run traversal mutations; (2) `Finish` is deliberately idempotent ("a spill yield re-enters this same arm" :7144) because `move_to_root_nonblock` there can itself spill after the tally is complete.

**Flow:** Start (clear saved seek, move_to_root_nonblock, yield if needed) → Loop {advance stack; if leaf/non-int-key add cell_count; walk up while exhausted; descend into rightmost-or-left-child page} → on read_page spill inside Loop: stash target in `Descend`, yield → Descend: retry ONLY read+advance+push → back to Loop … → exhausted ⇒ Finish ⇒ move_to_root_nonblock (idempotent on spill) ⇒ Done(count).
**Invariant:** every side effect (count +=, stack.advance/push/pop) happens either before the state transition that can yield, or in a state whose re-entry path provably skips it; a porter who leaves `count += cell_count()` reachable from the post-spill resume path silently inflates the tally once per spill.
**Probe:** `core/storage/btree.rs:12068` `count_survives_spill_yield_at_finalization` — arms `pager.arm_spill_yield_on_read(root_page, 1)` to force a real spill from the FINALIZING move_to_root (second read of root), asserts returned tally == true cell count; sibling `process_overflow_read_survives_spill_yield_from_next_chain_read` :12024 pins the same yield-injection harness for overflow reads.
**Coverage caveat:** `btree.rs` has one parse_partial line (4126) far from these ranges; graph resolves both symbols line-exact.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "CountState count_survives_spill_yield_at_finalization arm_spill_yield_on_read", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the pattern: one enum-of-states per resumable cursor method, stored as a dedicated slot, with a payload-carrying resume variant whenever IO sits between two mutations. Adapt the IOResult plumbing to your async runtime (async/await makes the problem invisible but the ordering still applies across await points). Omit the explicit `Descend` twin for methods whose only IO is at entry/exit (their Start/Finish states already cover it).

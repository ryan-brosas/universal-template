<!-- capsule-v2 -->
# HostProcesses ancestor immunity — why must kill/pkill refuse to signal this shell and its ancestors?

**Source:** oh-my-pi (see pack SKILL.md Provenance) MIT `main@4854db85`; Codebase Memory `oh-my-pi`. **Question:** How is the "protected chain" resolved so a recycled parent PID never inherits immunity, and where in the pipeline does refusal apply?

## HostProcesses resolve/walk
**Path/Symbol:** `crates/pi-builtins/src/proc_snapshot.rs:` `struct HostProcesses` (:1108-1113), `resolve()` (:1134-1136), `resolve_in(&[ProcInfo])` (:1141-1155), `fn walk` (:1167-1198); consumer gates `kill.rs:418 blocks_target`, `proc_match.rs:190` (pkill refuses at delivery).
**Signature:** `fn walk(self_pid: i32, lookup: impl Fn(i32) -> Option<ChainNode>) -> Self` — synthetic-lookup form exists so PID-recycling races are testable. Storage: `SmallVec<[i32; 16]>` for pids AND pgids.
**Data Shape:** `ChainNode { ppid: Option<i32>, pgid: Option<i32>, start: u64 }`; `HostProcesses { pids: self-first nearest→root, pgids: distinct groups along the chain }`.

### Decisive source
```rust
// A recorded parent pid is followed only when the process holding it is both
// PRESENT and NO YOUNGER THAN ITS CHILD. ... A real parent cannot have started
// after its child, so a later start time identifies the impostor. Equal start
// times are accepted, since a fork within one clock tick is indistinguishable.
if parent == 0 || pids.contains(&parent) { break; }   // pid 0 unsignallable; cycle closes walk
let Some(found) = lookup(parent) else { break; };
if found.start > current.start { break; }             // younger impostor stops the walk
```

**Flow:** resolve ONCE per command from one snapshot (`pkill` passes its selection snapshot to `resolve_in` to avoid a second table walk) → walk self → ppid → … collecting pids + pgids → signalling modes consult membership at DELIVERY time; listing modes (pgrep/ps) still REPORT ancestors.
**Invariant:** (1) Resolved-not-cached: a remembered chain would keep protecting a recycled pid after its previous owner exits. (2) Inline-not-hashed: a parent chain is 4–5 numbers; `chain_stays_in_inline_storage` asserts no heap spill — there is deliberately NO per-target query entry because it invites per-target re-resolves (full table walks). (3) Refusal is late (at delivery) so only destructive modes are affected — `pgrep` still lists the terminal. (4) `kill -1`/`kill 0` are refused wholesale (`blocks_target` returns true), own pgid needs no special case (it's in pgids by construction).
**Probe:** `crates/pi-builtins/src/proc_snapshot.rs:1222` `a_recycled_parent_pid_is_not_followed` (younger impostor excluded incl. its group), :1236 `an_older_parent_is_followed`, :1249 `a_same_tick_parent_is_followed`, :1260 `a_departed_parent_stops_the_walk`, :1267 `a_cyclic_parent_chain_terminates`, :1285 `chain_is_a_contiguous_parent_walk_over_observed_processes`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "HostProcesses walk recycled parent", limit: 10, fields: ["signature", "name", "file"] });
```
Live-resolved @4854db85: rank-1 `walk proc_snapshot.rs:1167-1198`.

## Verdict
Adopt whole: presence+age identity check, late delivery-time refusal, single-snapshot resolution, inline storage. This is the safety kernel that makes an embedded shell's own `pkill -f .` survivable. Adapt ChainNode plumbing if your snapshot type differs; omit nothing.

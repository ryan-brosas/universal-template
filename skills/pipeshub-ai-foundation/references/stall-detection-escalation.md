<!-- capsule-v2 -->
# Stall detection (POST_TURN tracker + PRE_MODEL escalation pair)

## Source
pipeshub-ai `main@4a02110d` — `hooks/middleware/builtin/stall_detection.py` (whole file, 134L).

## Path/Symbol
- `_StallState` dataclass (:32) — consecutive_error_turns, warned, total_error_calls, recent_error_tools (last 5 names)
- `_STALL_SLOT: StateSlot[_StallState]` keyed `"stall_detection.state"` (:40)
- `_is_error_heavy(turn, error_ratio)` (:54)
- `stall_detection(*, warn_after=3, fail_after=6, error_ratio=0.5)` (:62) — returns `(_post_turn, _pre_model)` PAIR

## Signature
POST_TURN middleware counts; PRE_MODEL middleware injects. State crosses turns via a module-level `StateSlot` on RunScope — per-run values, no leakage across runs sharing one kernel.

## Data Shape
"Error-heavy turn" = ≥ `error_ratio` (0.5 = majority) of the turn's tool results have `is_error`. Two injection tiers: soft warning at `warn_after` (once — `warned` latch), hard directive at `fail_after`.

## Decisive source
```python
elif state.consecutive_error_turns >= warn_after and not state.warned:
    state.warned = True   # soft warning fires exactly once per stall episode
```
Hard directive text mandates: completely different strategy OR task_complete with a partial answer — never repeat failing calls.

## Flow
POST_TURN: error-heavy → increment + record failing tool names; healthy turn → reset counter AND clear the warned latch (a new stall re-warns). PRE_MODEL: append warning/directive as a bracketed `[System: …]` UserMessage before the next model call.

## Invariant
**Recognition of stalls is programmatic, not probabilistic** — the agent cannot be trusted to notice its own loop. Escalation is monotone within an episode (warning → directive); reset happens only on a healthy turn.

## Probe
`tests/unit/agent_loop_lib/hooks/middleware/builtin/test_turn_guards.py` pins that `install_turn_guards()` does NOT install stall_detection unconditionally (`TestInstallTurnGuardsIsMinimal::test_does_not_install_supervisor_confidence_gate` :66) — it is OPT-IN via `install_stall_detection()`; ControlPlane wires it only for `hook_name == "stall_detection"` (control_plane.py :658). No direct behavior test for threshold math — coverage caveat recorded.

## Retrieve
`codebase-memory-mcp cli search_graph --project pipeshub-ai --semantic-query '["stall_detection","error heavy","StateSlot"]'`

## Verdict
ADOPT. The two-event middleware pair sharing StateSlot state is the reusable pattern for any cross-turn detector (stalls, loops, budget drift).

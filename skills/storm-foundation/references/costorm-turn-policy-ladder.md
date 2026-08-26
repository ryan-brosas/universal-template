<!-- capsule-v2 -->
# Co-STORM turn-policy ladder — who speaks next in a multiparty agent roundtable without a central scheduler?

**Source:** storm MIT `main@fb951af7`; Codebase Memory `storm`. **Question:** How do you decide which agent produces the next utterance in an unbounded multiparty conversation while preventing answer-domination and expert-list staleness?

## Turn-policy priority chain in DiscourseManager
**Path/Symbol:** `knowledge_storm/collaborative_storm/engine.py:DiscourseManager.get_next_turn_policy` (:461-502); helpers `_should_generate_question` (:408-423), `_is_last_turn_questioning` (:455-459), spec `TurnPolicySpec` (:293-316).
**Signature:** `get_next_turn_policy(conversation_history: List[ConversationTurn], dry_run=False, simulate_user=False, simulate_user_intent: str = None) -> TurnPolicySpec`.
**Data Shape:** `TurnPolicySpec` is a plain dataclass of three bools (`should_reorganize_knowledge_base`, `should_update_experts_list`, `should_polish_utterance`) + `agent`; the caller (`CoStormRunner.step`) executes each flag's side effect AFTER generating the utterance.

### Decisive source
```python
elif self.next_turn_moderator_override:
    next_turn_policy.agent = self.moderator
    if not dry_run:
        self.next_turn_moderator_override = False      # one-shot latch
...
if dry_run:
    next_turn_policy.agent = self.experts[0]           # peek WITHOUT rotating
else:
    next_turn_policy.agent = self.experts.pop(0)
    self.experts.append(next_turn_policy.agent)        # pop-front/push-back rotation
```

**Flow:** Priority chain top-down: (1) `simulate_user` → guest SimulatedUser with injected intent; (2) `rag_only_baseline_mode` → PureRAGAgent (asserts previous turn was role `"Guest"`); (3) `next_turn_moderator_override` → Moderator, consuming the latch only on a live run; (4) ≥N consecutive tail turns whose `utterance_type` is neither `Original Question` nor `Information Request` → Moderator AND `should_reorganize_knowledge_base=True`; (5) otherwise an expert turn: live runs rotate the experts deque via `pop(0)`/`append`, and when the last turn WAS a question the whole roster is regenerated from that focus (`should_update_experts_list=True`). Every expert turn sets `should_polish_utterance=True`.
**Invariant:** (1) The override latch must be consumed exactly once and only on non-dry-run calls, or a dry-run probe permanently disarms a moderator intervention — `warm_start()` sets it True right after seeding history so the first post-warmstart turn is always the Moderator's. (2) Dry-run policy resolution must be side-effect-free: peek `experts[0]`, never pop. (3) The moderator trigger counts only ANSWERING turns at the tail; a single new question resets the counter, which is what lets experts speak several turns in a row after one question. (4) Flag execution order in `step()` matters: expert-list refresh reads `last_conv_turn.raw_utterance` as the focus BEFORE the new turn is appended.
**Probe:** byte-pins executed this pass against engine.py — :381 `self.next_turn_moderator_override = False` init, :420-423 threshold comparison against `runner_argument.moderator_override_N_consecutive_answering_turn`, :487-490 dry-run peek vs live rotate branches, :616 override set True inside `warm_start()`. All line-exact.
**Coverage caveat:** engine.py checked `no_recorded_issue` @ gen 2026-08-25T20:09:07Z.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "storm", query: "get_next_turn_policy TurnPolicySpec moderator override experts rotate", limit: 10 });
```

## Verdict
Adopt the flag-spec + priority-chain shape for any turn-taking loop (it separates WHO acts from WHAT side effects follow); adapt thresholds and roster-regeneration triggers to your host; omit nothing on the latch/dry-run rules — consuming a latch during simulation or rotating during a dry run are the two corruption bugs this design guards against.

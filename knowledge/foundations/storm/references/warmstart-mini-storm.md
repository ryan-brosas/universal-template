<!-- capsule-v2 -->
# Warm-start mini-STORM — how do you bootstrap a fresh multi-agent session so turn one already has a shared knowledge base?

**Source:** storm MIT `main@fb951af7`; Codebase Memory `storm`. **Question:** What is the exact choreography that turns a bare topic into seeded experts, a populated mind map, and an engaging catch-up transcript before the first interactive turn?

## Four-step warm start with threaded expert chats and outline-first seeding
**Path/Symbol:** `knowledge_storm/collaborative_storm/modules/warmstart_hierarchical_chat.py:WarmStartModule.initiate_warm_start` (:346-408), `WarmStartConversation.forward` (:183-256), `ReportToConversation.forward` (:75-123); engine handoff `CoStormRunner.warm_start` (engine.py:582-640).
**Signature:** `initiate_warm_start(topic: str, knowledge_base: KnowledgeBase) -> Tuple[List[ConversationTurn], List[ConversationTurn], Optional[List[str]]]`.
**Data Shape:** Returns raw warmstart conv, revised "engaging" conv, expert strings (`"Name: description"` — the colon split is load-bearing at :197).

### Decisive source
```python
knowledge_base.insert_from_outline_string(outline_string=warm_start_outline_output.outline)
for turn in warm_start_conversation_history:
    knowledge_base.update_from_conv_turn(conv_turn=turn, allow_create_new_node=False)
...
self.discourse_manager.next_turn_moderator_override = True
self.conversation_history = (warmstart_revised_conv if warmstart_revised_conv
                             else warmstart_conv)
```

**Flow:** Step 1 — background Q&A in `extensive` mode ("Default Background Researcher", utterance_type `"Questioning"`), then `GenerateExpertModule` proposes `warmstart_max_num_experts` perspectives; a `ThreadPoolExecutor(max_thread)` runs each expert for up to `max_turn_per_experts` rounds: the moderator drafts the next question conditioned on the numbered history of prior claims (read under a shared Lock), `AnswerQuestionModule` answers, the turn is appended under the same Lock; ANY exception prints and swallows so one broken expert never kills the fleet. Step 2 — outline via draft-then-refine: a topic-only draft from storm_wiki's own `WritePageOutline`, refined against discussion-focus+query lines extracted per turn. Step 3 — KB seeding is outline-FIRST then info placement with `allow_create_new_node=False`, so placement can only fill the skeleton. Step 4 — `to_report()` synthesizes node content, then `ReportToConversation` converts every non-root content-bearing node into a moderator-question/expert-answer ConversationTurn pair (parallel over nodes; citations rebound through `parse_citation_indices`). Engine side: history is seeded with the REVISED conv (raw as fallback), raw archived separately, moderator override latched True, one reorganize.
**Invariant:** (1) Outline-before-info ordering is what makes `allow_create_new_node=False` safe — invert it and placement raises on missing nodes or silently drops info. (2) The lock guards BOTH the history read (question context) and the append; reading outside the lock races the pool. (3) Swallowed exceptions are per-expert isolation by design, but they make partial warm starts silent — detect them via turn counts, not logs. (4) The revised conv REPLACES raw conv as live history while raw is archived; citation indices differ between the two, so never mix turns across the two lists.
**Probe:** byte-pins executed this pass — :197 `expert.split(":")`, :203/:237 lock-guarded read/append, :239-240 print-and-swallow except, :387-394 outline-then-turns seeding order with `allow_create_new_node=False`, :616 override latch, :617-620 revised-over-raw selection. All line-exact against the checkout.
**Coverage caveat:** file checked `no_recorded_issue` @ gen 2026-08-25T20:09:07Z.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "storm", query: "WarmStartModule initiate_warm_start ReportToConversation GenerateWarmStartOutlineModule", limit: 10 });
```

## Verdict
Adopt the four-step choreography (background research → perspectives → outline-first KB seed → synthesized catch-up transcript) for any agent system that must start "hot"; adapt step budgets and expert-count args; omit nothing on the lock discipline and list-replacement semantics — they are the difference between a clean bootstrap and a silently half-seeded session.

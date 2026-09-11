<!-- capsule-v2 -->
# Flow-wiring validation — how do you turn declarative communication_flows into per-pair tools without duplicate or silent routes?

**Source:** agency-swarm MIT `main@4d1c35a6dd5ef038a5d15b39803459ff0b5f5578`; Codebase Memory `ext-agency-swarm`. **Question:** What is the exact validation ladder that maps `(sender, receiver)` declarations to SendMessage/Handoff instances, and which duplicates must RAISE versus silently coalesce?

## parse_agent_flows → configure_agents two-stage wiring
**Path/Symbol:** `src/agency_swarm/agency/setup.py:parse_agent_flows` (:82-182), `_add_tool_class_for_pair` (:33-60), `_add_default_tool_pair` (:63-79), `configure_agents` (:237-322), `register_all_agents_and_set_entry_points` (:185-219); entry-shape union in `src/agency_swarm/agency/flow_compat.py:CommunicationFlowEntry`.
**Signature:** `parse_agent_flows(agency, communication_flows) -> tuple[list[tuple[Agent, Agent]], dict[tuple[str, str], list[type]], set[tuple[str, str]]]`; `configure_agents(agency, defined_communication_flows) -> None`.
**Data Shape:** three artifacts: basic flows (ordered unique pairs), tool-class mapping keyed `(sender_name, receiver_name) → list[type]`, and a set of pairs that requested the DEFAULT send_message. Flow entries: `(Agent, Agent)` default pair · `(Agent, Agent, type|list[type])` custom classes · `(AgentFlow, type|None)` chains from the `agent1 > agent2 > agent3` operator.

### Decisive source
```python
# Duplicate detection distinguishes THREE failure classes:
if pair_key in default_tool_pairs and issubclass(tool_class, SendMessage):
    raise ValueError(f"Duplicate communication tool class detected for {pair_key[0]} -> {pair_key[1]}: ...")
classes = mapping.setdefault(pair_key, [])
for existing_tool_class in classes:
    if issubclass(existing_tool_class, SendMessage):     # second SendMessage for same pair RAISES
        raise ValueError("Duplicate communication tool class detected ...")
if tool_class in classes:                                # same class twice RAISES
    raise ValueError(...)
classes.append(tool_class)                               # Handoff variants may COEXIST (list)
...
# configure_agents: default fallback + per-pair override composition
tool_classes = []
if pair_key in agency._default_communication_tool_pairs:
    tool_classes.append(agency.send_message_tool_class or SendMessage)
tool_classes.extend(configured)
if not tool_classes:
    tool_classes.append(agency.send_message_tool_class or SendMessage)   # undeclared pair still gets a route
```

**Flow:** capture AgentFlow chain-flows once (`AgentFlow.get_and_clear_chain_flows()` — global accumulator drained at parse start so repeated tuples don't double-register) → normalize each entry into pair + optional classes → register agents by IDENTITY (`id()`), rejecting duplicate names with different instances (`register_agent`) → build per-sender communication map → for each allowed recipient instantiate every effective class: Handoff subclasses become `handoff()` objects appended to `runtime_state.handoffs`, SendMessage subclasses are registered via `register_subagent`; receive-only agents raise if declared as senders; registration errors log-and-continue so one bad pair never kills the whole agency.
**Invariant:** (1) A pair can carry AT MOST ONE SendMessage subclass but MULTIPLE Handoff variants — the mapping value is a list only because of handoffs; (2) an undeclared-but-registered pair still receives the default/fallback tool — silence would strand the LLM without a delegation path it can name; (3) chain flows are captured exactly once per Agency construction (the `chain_flows_used` latch); (4) legacy 2-tuple parser results are normalized to the 3-tuple shape in flow_compat (`normalize_parse_agent_flows_result`) so local patches can't crash init.
**Probe:** `tests/test_agency_modules/test_agent_flow_integration.py::test_duplicate_communication_tool_class_is_rejected` (:261), `test_unsupported_communication_tool_class_is_rejected` (:285), `test_empty_communication_tool_class_list_is_rejected` (:299), `test_duplicate_flow_detection_with_chains` (:308), `test_runtime_registration_keeps_multiple_send_message_tool_classes` (:157), `test_legacy_two_value_flow_parser_patch_still_initializes_agency` (:139).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-agency-swarm", query: "parse_agent_flows configure_agents communication tool class", limit: 10 });
```

## Verdict
Adopt the fail-loud duplicate taxonomy (default-pair vs custom vs same-class) plus the always-give-a-route fallback; adapt entry-shape normalization to your own DSL; omit the operator-overload chain syntax (`__gt__`/`__lt__` on Agent) if you take flows as data. Six direct tests pin the rejection ladder at HEAD.

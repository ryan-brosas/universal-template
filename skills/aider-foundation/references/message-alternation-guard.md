<!-- capsule-v2 -->
# Message alternation guard — strict validator raises, lenient repair inserts empty turns

**Source:** Aider Apache-2.0 `main@5dc9490bb35f9729ef2c95d00a19ccd30c26339c`; Codebase Memory project `aider`. **Question:** How does an agent keep a strict provider-side user/assistant alternation contract when history surgery (summarization, reflection loops) keeps producing consecutive same-role messages?

## Two functions, two postures: validate-and-raise before send, repair-by-insert after history edits
**Path/Symbol:** `aider/sendchat.py`: `sanity_check_messages(messages)` (:5), `ensure_alternating_roles(messages)` (:29); consumers in `aider/models.py` (`simple_send_with_retries` path) and base_coder history assembly.
**Signature:** `sanity_check_messages(messages) -> bool` raises `ValueError("Messages don't properly alternate user/assistant:\n\n" + format_messages(messages))` on any adjacent same-role pair; returns whether the last non-system message is user. `ensure_alternating_roles(messages) -> list` never mutates input; appends `{"role": "assistant"/"user", "content": ""}` of the OPPOSITE role before each offender.
**Data Shape:** system messages are transparent to BOTH functions — they may appear anywhere and never reset `last_role`.

### Decisive source
```python
for msg in messages:
    role = msg.get("role")
    if role == "system":
        continue
    if last_role and role == last_role:
        turns = format_messages(messages)
        raise ValueError("Messages don't properly alternate ...")
    ...
# repair side:
if current_role == prev_role:
    if current_role == "user":
        fixed_messages.append({"role": "assistant", "content": ""})
    else:
        fixed_messages.append({"role": "user", "content": ""})
```

**Flow:** pre-flight: raise with the FULL formatted transcript so the developer sees where alternation broke; history-repair path: rebuild a new list inserting minimal empty filler turns. The final-gate return value (`last_non_system_role == "user"`) encodes aider's convention that a request always ends with the user speaking.
**Invariant:** empty-string content is the canonical filler — providers accept it and it renders invisibly in transcripts; the repair function's output re-passes the validator by construction. EXECUTED BEHAVIOR PROBE this run: `[user,user]` → inserts empty assistant between (exact list equality green).
**Probe:** direct tests executed GREEN this run via repo venv (`python -m pytest tests/basic/test_sendchat.py -q`: **12 passed**): `test_ensure_alternating_roles_consecutive_user` (:121), `_consecutive_assistant` (:136), `_mixed_sequence` (:151) pin exact output lists including filler placement; `test_litellm_exceptions` (:18) runs the strict exception-table load.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "aider", query: "ensure_alternating_roles", limit: 3 });
// rank-1: aider.aider.sendchat.ensure_alternating_roles aider/sendchat.py 29-61
```

## Verdict
Adopt both postures verbatim — strict gate at the wire, lenient repair at the history layer — this split is what lets summarizers/reflection loops mutate chat state freely without ever shipping an invalid payload.

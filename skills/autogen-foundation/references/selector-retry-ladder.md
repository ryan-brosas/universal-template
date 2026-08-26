<!-- capsule-v2 -->
# Selector retry ladder — how do you make an unreliable LLM produce a valid speaker choice?

**Source:** autogen (MIT — LICENSE-CODE) `main@027ecf0a...`; Codebase Memory `ext-autogen`. **Question:** What is the validation-feedback-fallback loop for LLM speaker selection, and how are agent names matched in free text?

## Grow-the-conversation retries, then deterministic fallback
**Path/Symbol:** `python/packages/autogen-agentchat/src/autogen_agentchat/teams/_group_chat/_selector_group_chat.py` (`_select_speaker` :232–308, `_mentioned_agents` :310–341).
**Signature:** `async def _select_speaker(self, roles: str, participants: List[str], max_attempts: int) -> str`.
**Data Shape:** Conversation list grows with each failed attempt: system/user prompt → assistant reply → user feedback → ...; success = exactly ONE mentioned participant passing the repeat-speaker rule.

### Decisive source
```python
elif len(mentions) > 1:
    feedback = (f"Expected exactly one name to be mentioned. Please select only one from: {str(participants)}.")
    select_speaker_messages.append(UserMessage(content=feedback, source="user"))
...
if self._previous_speaker is not None:
    trace_logger.warning(f"Model failed to select a speaker after {max_attempts}, using the previous speaker.")
    return self._previous_speaker
return participants[0]        # no previous speaker -> first participant
```
```python
# mention matching: exact | underscores-as-spaces | escaped-underscores, word-bounded
regex = (r"(?<=\W)(" + re.escape(name) + r"|" + re.escape(name.replace("_", " "))
         + r"|" + re.escape(name.replace("_", r"\_")) + r")(?=\W)")
count = len(re.findall(regex, f" {message_content} "))   # pad BOTH ends so boundary lookarounds hit
```

**Flow:** build prompt from `{roles}/{participants}/{history}` → model reply → count mentions via three-variant regex → zero/multi/repeated-speaker each append a SPECIFIC corrective feedback message and retry → after `max_selector_attempts` failures return previous speaker if any, else first participant.
**Invariant:** feedback messages name the EXACT violation class (none / multiple / repeated) — generic "invalid" feedback measurably degrades retry success; the repeat check uses ALL participant names for mention-counting even when the previous speaker was excluded from candidates ("NOTE: we use all participant names..." :272–274) because exclusion happens at candidate-filtering, not mention detection; padding with spaces is REQUIRED or leading/trailing names never match the `\W` lookarounds.
**Probe:** `python/packages/autogen-agentchat/tests/test_group_chat.py::test_selector_group_chat_succcess_after_2_attempts`, `::test_selector_group_chat_fall_back_to_first_after_3_attempts`, `::test_selector_group_chat_fall_back_to_previous_after_3_attempts` (each fallback branch pinned with a ReplayChatCompletionClient).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-autogen", query: "_select_speaker _mentioned_agents max_selector_attempts allow_repeated_speaker", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt violation-specific feedback retries with a two-tier deterministic fallback for any constrained-output LLM call. Adapt the mention matcher to your tokenizer (this one assumes names appear verbatim). Omit the OpenAI-family SystemMessage vs UserMessage branch (:241–245) if your models accept system prompts.

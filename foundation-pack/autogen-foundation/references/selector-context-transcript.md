<!-- capsule-v2 -->
# Selector context transcript — how does an LLM speaker-selector see the conversation without blowing its own budget?

**Source:** autogen (MIT — LICENSE-CODE) `main@027ecf0a379bcc1d09956d46d12d44a3ad9cee14`; Codebase Memory project `autogen` (FULL, 16,432 nodes / 86,358 edges, generation 2026-08-24T16:12:29Z). **Question:** Where does truncation live for the selector's view of the thread, and what state must the selector persist across turns?

## Pluggable ChatCompletionContext flattened into ONE prompt message
**Path/Symbol:** `python/packages/autogen-agentchat/src/autogen_agentchat/teams/_group_chat/_selector_group_chat.py` `SelectorGroupChatManager.__init__` :99–103 (default `UnboundedChatCompletionContext()`), `_add_messages_to_context` :133–145, `select_speaker` :152–217, `_select_speaker` :232–308, `construct_message_history` :219–230, save/load_state :116–131.
**Signature:** `async def select_speaker(self, thread) -> List[str] | str` · `def construct_message_history(self, message_history: List[LLMMessage]) -> str` · state shape `{message_thread: [dumped], current_turn: int, previous_speaker: str | None}`.
**Data Shape:** selector prompt = `selector_prompt.format(roles=..., participants=str(list), history=<flattened transcript>)`, sent as ONE SystemMessage (OpenAI model family) or UserMessage (everything else); retry feedback appends AssistantMessage(source="selector") + feedback UserMessages to a per-turn scratchpad list.

### Decisive source
```python
model_context_messages = await self._model_context.get_messages()   # truncation happens HERE, in the context
model_context_history = self.construct_message_history(model_context_messages)
select_speaker_prompt = self._selector_prompt.format(roles=roles, participants=str(participants), history=model_context_history)
if ModelFamily.is_openai(self._model_client.model_info["family"]):
    select_speaker_messages = [SystemMessage(content=select_speaker_prompt)]
else:
    # Many other models need a UserMessage to respond to
    select_speaker_messages = [UserMessage(content=select_speaker_prompt, source="user")]
```
```python
# HandoffMessage.context carry-over is expanded into the selector's view too
for msg in messages:
    if isinstance(msg, HandoffMessage):
        for llm_msg in msg.context:
            await model_context.add_message(llm_msg)
    await model_context.add_message(msg.to_model_message())
```

**Flow:** every delivered chat message is appended to BOTH the raw `_message_thread` and the pluggable `_model_context` → on each turn: optional selector_func override (validated against participant names) → candidate_func filter or previous-speaker exclusion when repeats disallowed → single candidate skips the LLM entirely → otherwise flatten context to "source: content\n\n" transcript, interpolate, one completion → mention-count verdict feeds the retry ladder (see selector-retry-ladder) → on success set `_previous_speaker` and return `[name]`.
**Invariant:** the manager itself NEVER truncates — windowing is fully delegated to whichever ChatCompletionContext was injected (default unbounded); `_previous_speaker` filters candidates but mention-checking deliberately uses ALL names so a repeated pick can be caught with tailored feedback; selector state persists thread+turn+previous_speaker, and reset clears all three plus the context.
**Probe:** `python/packages/autogen-agentchat/tests/test_group_chat.py::test_selector_group_chat_with_model_context` (:823–874 — BufferedChatCompletionContext(buffer_size=5) injected; every captured create call's prompt contains only a sliding ~5-message slice of history, proving the injected context bounds the transcript).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "autogen", qn_pattern: "^autogen\\.python\\.packages\\.autogen-agentchat\\.src\\.autogen_agentchat\\.teams\\._group_chat\\._selector_group_chat\\.SelectorGroupChatManager\\.", limit: 20 });
```

## Verdict
Adopt "selector sees a transcript string whose window is someone else's policy" — inject your own bounded context instead of special-casing the manager. Adapt the model-family System/User role choice and the mention regex to your models. Omit the deprecated two-arg factories nearby; keep the per-turn retry scratchpad separate from the long-lived context so feedback never pollutes later turns' base history.

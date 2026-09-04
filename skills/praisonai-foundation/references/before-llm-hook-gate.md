<!-- capsule-v2 -->
# BEFORE_LLM hook gate — how do blocking hooks/plugins refuse an LLM dispatch instead of failing open?

**Source:** praisonai MIT `main@d82364ec23a83fd9a6e2e849a5285442b4734ca3`; Codebase Memory `praisonai`. **Question:** When a registered hook or plugin denies the upcoming LLM call (policy/guardrail), how does the dispatch path refuse without ever hitting the provider — and how does a hook that only *mutates* messages (e.g. PII redactor) get adopted for the real call?

## ChatMixin._chat_completion hook gate
**Path/Symbol:** `src/praisonai-agents/praisonaiagents/agent/chat_mixin.py:ChatMixin._chat_completion` (lines 1771–1807; async parity twin in `_execute_unified_achat_completion` lines 2526–2560).
**Signature:** gate runs inside `_chat_completion(self, messages, temperature=None, tools=None, stream=None, ..., _retry_depth=0, _fallback_index=0)`; input object `BeforeLLMInput(session_id, cwd, event_name, timestamp, agent_name, messages, model, temperature)`; output: refusal string on block, otherwise the (possibly mutated) message list used for the actual provider call.

### Decisive source
```python
if self._hook_runner.registry.has_hooks(HookEvent.BEFORE_LLM):
    before_llm_input = BeforeLLMInput(
        session_id=getattr(self, '_session_id', 'default'),
        cwd=os.getcwd(), event_name=HookEvent.BEFORE_LLM,
        timestamp=str(time.time()), agent_name=self.name,
        messages=messages,
        model=self.llm if isinstance(self.llm, str) else str(self.llm),
        temperature=temperature
    )
    _before_llm_results = self._hook_runner.execute_sync(HookEvent.BEFORE_LLM, before_llm_input)
    # Honour a blocking BEFORE_LLM hook/plugin (POLICY/GUARDRAIL) by
    # refusing to dispatch the request, mirroring how BEFORE_TOOL/BEFORE_AGENT
    # enforce blocks. Without this, a plugin that returns PluginDecision.deny()
    # (or raises GuardrailBlocked) would fail open and still hit the model.
    if self._hook_runner.is_blocked(_before_llm_results):
        _block_reason = next(
            (getattr(r.output, "reason", None) for r in _before_llm_results
             if r.output and getattr(r.output, "is_denied", lambda: False)()),
            None,
        ) or "Blocked by hook"
        logging.warning(f"Agent {self.name} LLM request blocked by BEFORE_LLM hook: {_block_reason}")
        return f"[LLM request blocked by hook: {_block_reason}]"
    # C7 - honour any BEFORE_LLM hook that mutated the message stream
    # (e.g. PII redactor). The runner applies modified_input in-place on
    # before_llm_input.messages; adopt that value for the actual LLM call.
    messages = before_llm_input.messages
```

**Flow:** zero-overhead gate (`has_hooks` check skips input construction entirely when nothing is registered) → build `BeforeLLMInput` → `execute_sync` all BEFORE_LLM hooks/plugins → `is_blocked(results)` → if blocked: extract reason from the first denied output's `.reason` (fallback literal "Blocked by hook"), log warning, **return a refusal string and never dispatch** → otherwise adopt `before_llm_input.messages` (the runner applies hook mutations in place) as the message list for the real provider call.
**Invariant:** a denied BEFORE_LLM result must never reach the provider — the failure mode being prevented is fail-open (deny decision or raised GuardrailBlocked silently hitting the model); the exact bytes sent to the LLM are the hook-mutated messages, not the pre-hook list; unregistered hooks cost nothing.
**Probe:** `tests/unit/plugins/test_hook_bridge.py:220–245` pins the predicate this gate calls — a deny-decision plugin makes `runner.is_blocked(results) is True`, and a guardrail that *raises* Block also yields `is_blocked is True` with `get_blocking_reason(results) == "Secret detected in tool output"`. The refusal-string path inside `_chat_completion` itself has no direct test → deterministic read caveat.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "praisonai", query: "BEFORE_LLM hook blocked refuse dispatch", name_pattern: "^is_blocked$|^BeforeLLMInput$", limit: 10 });
```

## Verdict
Adopt the three-part contract: (1) registry-presence gate so the hot path pays nothing when no hooks exist, (2) fail-closed block that returns a *string refusal* (not an exception) so callers can surface the reason to the user, (3) in-place mutation adoption for non-blocking hooks. Adapt the hook-runner API (`execute_sync`/`is_blocked`/`get_blocking_reason`) and the `PluginDecision.deny()`/GuardrailBlocked vocabulary to your host's plugin system. Omit praisonai's specific `BeforeLLMInput` field set (session_id/cwd/timestamp) beyond what your host needs. Coverage: chat_mixin.py has no recorded index issue; the `is_blocked` predicate is directly tested, the `_chat_completion` wiring of it is not — verify by trace before porting.

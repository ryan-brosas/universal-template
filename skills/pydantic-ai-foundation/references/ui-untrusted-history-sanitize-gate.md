<!-- capsule-v2 -->
# Untrusted-history sanitizer gate — which parts of a client-submitted message history may an HTTP adapter trust?

**Source:** pydantic-ai Apache-2.0 `main@fde1bbb6aff461769a1d6d2440c33c232bf90f03`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** When the frontend sends conversation history over the wire, what must be stripped before it reaches the agent, and how does human-in-the-loop resume survive that stripping?

## UIAdapter.sanitize_messages
**Path/Symbol:** `pydantic_ai_slim/pydantic_ai/ui/_adapter.py:` `UIAdapter.sanitize_messages` (:395–438), resolved-id collection (:426–429); compaction guard `_drop_compaction_parts` applied in `run_stream_native` (:520–524); underlying engine `messages.sanitize_messages`.
**Signature:** `def sanitize_messages(self, messages: Sequence[ModelMessage], *, deferred_tool_results: DeferredToolResults | None = None) -> list[ModelMessage]`.
**Data Shape:** knobs: `strip_system_prompts = (self.manage_system_prompt == 'server')`, `allowed_file_url_schemes`, `allowed_file_url_force_download`, `allow_uploaded_files`, `resolved_tool_call_ids: set[str]` from `deferred_tool_results.approvals ∪ .calls`.

### Decisive source
```python
resolved_tool_call_ids: set[str] = set()
if deferred_tool_results is not None:
    resolved_tool_call_ids.update(deferred_tool_results.approvals)
    resolved_tool_call_ids.update(deferred_tool_results.calls)

return sanitize_messages(
    messages,
    strip_system_prompts=self.manage_system_prompt == 'server',
    allowed_file_url_schemes=self.allowed_file_url_schemes,
    allowed_file_url_force_download=self.allowed_file_url_force_download,
    allow_uploaded_files=self.allow_uploaded_files,
    resolved_tool_call_ids=resolved_tool_call_ids,
)

# run_stream_native:
frontend_messages = self.sanitize_messages(self.messages, deferred_tool_results=deferred_tool_results)
if message_history:
    # A client-supplied compaction part would trim the trusted server-side history off the
    # wire, so only the server's own boundaries are honored. See `_drop_compaction_parts`.
    frontend_messages = _drop_compaction_parts(frontend_messages)
message_history = [*(message_history or []), *frontend_messages]
```

**Flow:** client body → protocol run input → `.messages` → sanitize (strip system prompts when server-managed — they're reinjected by `ReinjectSystemPrompt`; filter file URLs by scheme allowlist; drop uploaded files unless enabled; KEEP trailing tool calls whose ids appear in deferred approvals/calls so HITL resumption works) → separately, client-sent COMPACTION markers are dropped wholesale because a forged compaction part would erase real server-side history → merged AFTER any caller-supplied trusted history.
**Invariant:** three rules:
1. Trust boundary is per-source, not per-message: client-supplied `message_history` args are TRUSTED (server persistence), only protocol-run-input messages pass through the sanitizer — never sanitize both with the same strictness.
2. A compaction marker from the client is a history-truncation attack vector; only server-planted boundaries are honored.
3. HITL legality carve-out: stripping tool calls without results would break approval-resume, so the resolved-id set re-admits exactly those calls.
**Probe:** `grep -c 'resolved_tool_call_ids' pydantic_ai_slim/pydantic_ai/ui/_adapter.py` = 4 (anchored at repo root; 1 init + 2 updates + 1 kwarg) and `.venv/bin/python -m pytest tests/test_ui.py -k 'sanitize' -p no:cacheprovider` = 18 passed (anchored at repo root; adapter-level suites).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "sanitize_messages resolved_tool_call_ids strip_system_prompts", limit: 8, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the per-source trust split and the compaction-marker rule for ANY agent HTTP surface accepting history; adapt the strip-list to your message schema; omit the file-URL knobs if your transport disallows file parts.

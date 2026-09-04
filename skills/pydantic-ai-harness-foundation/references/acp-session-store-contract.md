<!-- capsule-v2 -->
# ACP session store contract — which store failures fail the user's request and which must never?

## Source / Question
`pydantic_ai_harness` (MIT) `main@76db3dec`; Codebase Memory project `pydantic-ai-harness`. **Question:** A durable session store sits behind an already-streamed conversation — when its `save` raises versus when its `load` raises, which failure may surface to the client, what error shape must it take, and how do you reopen a session id that is still live without letting the orphaned turn corrupt the restore?

## Path / Symbol
`pydantic_ai_harness/experimental/acp/_store.py` — `StoredSession` (:22–32), `SessionStore` Protocol (:35–51); `pydantic_ai_harness/experimental/acp/_adapter.py` — `_persist` (:386–402), `load_session` (:328–384).

**Signature:**
```python
class StoredSession:  # messages: list[ModelMessage]; updates: list[SessionUpdate]; model: str | None
class SessionStore(Protocol):
    async def save(self, session_id: str, session: StoredSession) -> None: ...
    async def load(self, session_id: str) -> StoredSession | None: ...
async def _persist(self, state: SessionState[AgentDepsT]) -> None
async def load_session(self, cwd: str, session_id: str, mcp_servers: McpServers = None,
                       additional_directories: list[str] | None = None, **kwargs) -> schema.LoadSessionResponse | None
```

**Data Shape:** `StoredSession` holds only Pydantic-serializable models (whole `SessionUpdate` union must survive a JSON round-trip) plus the config-selected model id so a reopened session keeps it. `save` is called once at session creation and after every committed turn; `load` returns the stored session or `None` for unknown ids.

### Decisive source
Protocol contract docstring (:35–51): "a `save` that raises is logged and swallowed ... that work already streamed and committed in memory ...; the next successful save catches the store up. A `load` that raises ... fails `session/load` with an `internal_error`, since a session that cannot be read cannot be reopened." And the takeover ladder (:371–377):
```python
        # A client may load a session id that is still open (a reconnecting editor, or a double
        # load). Tear down any live turn first so the orphaned turn cannot later persist its stale
        # state over the transcript and history we are about to restore.
        prior = self._sessions.pop(session_id, None)
        if prior is not None:
            await self._cancel_active_turn(prior)
```
Plus purpose-built load errors (:352–362): read/deserialize failure → `acp.RequestError.internal_error({'session_id':…, 'reason': 'stored session could not be read'})` chained from the store exception; unknown id → `invalid_params('no stored session with this id')`; no store configured → `method_not_found('session/load')`.

**Flow:** commit → `_persist(state)` snapshots `list(history)/list(transcript)/model` → store errors logged (`'failed to persist ACP session %s; durable state is now behind'`) and swallowed. `session/load`: capability gate → store read → error translation → unknown-id rejection → cancel-and-pop any live state (a queued prompt holding the REPLACED state later fails with RequestError rather than committing orphaned history over the restored session) → rebuild config from cwd/mcp_servers → replay stored `updates` verbatim to the client (leading with the recorded user message the live client never received) → respond with refreshed model config options.

**Invariant:** Asymmetric durability: write failures are progress-not-failure (log + catch up next save); read failures are hard errors in purpose-built ACP form (never leak pydantic validation detail). Restore replaces in-memory state atomically AFTER the old state's turn is torn down, so exactly one writer owns a session id.

**Probe:** `bash -c 'cd $REFERENCE_ROOT/pydantic-ai-harness && /tmp/harness-p6-venv/bin/python -m pytest tests/experimental/acp/test_persistence.py -q'` — 13 tests: Pydantic round-trip of StoredSession, advertise-load-only-with-store, empty-session persist, transcript == recorded-user-prompt + shown updates, replay-on-reopen, load-cancels-in-flight-turn, queued-prompt orphan rejected while store keeps snapshot, close-then-load, unknown id, method_not_found without store, post-commit-save cancel, save-failure logged with 'end_turn', set-config save-failure, load-read-failure code −32603 'could not be read'. (Full module executed this pass; see verification.md.)

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pydantic-ai-harness", query: "SessionStore StoredSession load_session stored session could not be read", limit: 5 });
```
Observed live: rank#1 `StoredSession` (_store.py :22–32), `SessionStore` protocol (:35–51) adjacent; `PydanticAIACPAgent.load_session` (:328–384) resolves with test_persistence callers.

## Verdict
**Adopt** the asymmetric failure contract verbatim for any cache/store behind user-visible work: writes fail soft (logged, self-healing on next write), reads fail loud (typed protocol error, sanitized detail). **Adopt** pop-then-cancel takeover before restoring live-session ids, and the queued-request rejection that follows from it. **Adopt** persisting only Pydantic-round-trippable shapes (test the whole update union, not just produced variants). **Adapt** error codes/wording to your RPC surface. **Omit** the ACP SDK routing quirks (method_not_found for advertised-off methods is protocol-specific). Caveat: none — the dedicated persistence suite pins every branch at this pin.

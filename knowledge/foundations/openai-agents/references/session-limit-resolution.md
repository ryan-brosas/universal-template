<!-- capsule-v2 -->
# Session limit resolution — how does an explicit per-call limit interact with configured session defaults?

**Source:** OpenAI Agents Python MIT `main@cb8a2e7e`; Codebase Memory project `openai-agents-python`. **Question:** What is the precedence ladder for history limits, and what does limit=0 mean?

## Explicit-over-settings precedence
**Path/Symbol:** `src/agents/memory/session_settings.py:` `resolve_session_limit` (:18–27), `SessionSettings.resolve` (:41–60), `coerce_session_settings` (:67–71); consumption in `SQLiteSession.get_items` (:268–338) and `prepare_input_with_session` (:350–357).
**Signature:** `def resolve_session_limit(explicit_limit: int | None, settings: SessionSettings | dict[str, Any] | None) -> int | None`.
**Data Shape:** `limit: int | None`; overlay semantics = non-None override fields replace base values via `dataclasses.replace`.

### Decisive source
```python
if explicit_limit is not None:
    return explicit_limit
if settings is not None:
    return coerce_session_settings(settings).limit
return None   # unlimited
```
Runtime meaning (SQLite): `None` ⇒ full history ASC; `> 0` ⇒ latest-N with the corrupt-row window-expansion loop; `<= 0` (incl. negatives) ⇒ passed through to SQL LIMIT, preserving SQLite's historical semantics (0 = nothing; negative = UNLIMITED in SQLite) rather than being "fixed".

**Flow:** constructor coerces dict-or-dataclass into typed settings → per call, explicit argument wins over instance settings → overlay produces a NEW object (base never mutated) so shared sessions aren't corrupted by one caller's override.

**Invariant:** `0` must stay distinct from `None`: zero means "no history", None means "all"; overrides are immutable overlays — resolving must not mutate the session's own settings.

**Probe:** `tests/memory/test_session_limit.py::test_session_limit_zero` (:126), `test_session_limit_none_gets_all_history` (:163), `test_session_limit_parameter` (:19).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openai-agents-python", query: "resolve session limit settings overlay", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the explicit→configured→unlimited ladder and the 0-vs-None distinction for any paged/capped store API; adapt coercion helpers to your config system.

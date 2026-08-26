<!-- capsule-v2 -->
# Evolve sentinel identifiers — how do you keep placeholder user IDs ("default") out of an external memory service?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** Before attributing memories/facts/trajectories to a user, which identifier values must be treated as "no user"?

## normalize_evolve_identifier
**Path/Symbol:** `src/cuga/backend/evolve/integration.py:19-32` (`_EVOLVE_SENTINEL_IDS`, `normalize_evolve_identifier`); applied at every entry point (`get_guidelines` :68-70, `save_trajectory` :164-166); trajectory save gate :156-161; message conversion :198-217.
**Signature:** `normalize_evolve_identifier(value: Optional[str]) -> Optional[str]`.
**Data Shape:** sentinels = `{"default", "default_user"}` — "`default` is AgentState.user_id's default; `default_user` is the server's DEFAULT_USER_ID for unauthenticated requests."

### Decisive source
```python
_EVOLVE_SENTINEL_IDS = {"default", "default_user"}

def normalize_evolve_identifier(value: Optional[str]) -> Optional[str]:
    """Return None for empty or sentinel placeholders so Evolve only sees real ids."""
    if value is None:
        return None
    stripped = str(value).strip()
    if not stripped or stripped in _EVOLVE_SENTINEL_IDS:
        return None
    return stripped
```
Save-side gating (:156-161):
```python
if success and not settings.evolve.save_on_success:
    return
if not success and not settings.evolve.save_on_failure:
    return
```

**Flow:** any identifier entering Evolve (user_id / namespace_id / session_id) is normalized first — None/blank/sentinel ⇒ omitted from the tool args entirely, never sent as a literal string → trajectories converted to OpenAI role format keeping ONLY human/assistant messages (system/tool messages skipped; empty content skipped) → saves gated independently per outcome by `save_on_success` / `save_on_failure`.
**Invariant:** placeholder identities must NEVER become durable memory keys — two different anonymous sessions would otherwise share one "default" memory space and leak facts across users; conversion drops non-conversational messages rather than coercing them.
**Probe:** direct tests in `src/cuga/backend/evolve/tests/test_integration.py`: message conversion (:55-90: converts human+ai, skips system, skips empty content, handles non-string content), enable-gate matrix (:24-48), disabled no-op paths (:105-123, :143), payload passthrough (:151). Sentinel set itself verified by source read + call-site grep (normalized before every `_call_tool` that carries ids).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "normalize_evolve_identifier _EVOLVE_SENTINEL_IDS", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the sentinel-set normalization for ANY cross-service identity handoff where the host framework has default placeholder ids; adapt the sentinel values to your framework's defaults; adopt the per-outcome save gates as config surface; omit namespace/session handling if your service has no scoping. Direct tests pin conversion + gating; sentinel list is source-pinned.

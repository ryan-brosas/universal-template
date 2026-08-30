<!-- capsule-v2 -->
# Session knowledge provider — deep-merge overrides, ownership checks, and write-through persistence with prefix conventions

**Source:** cuga-agent Apache-2.0 `main@5de53ade`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** How do you store per-session and per-agent-version knowledge state (files, config overrides) so sequential PATCHes never clobber siblings, ownership survives creation-via-patch, and restarts lose nothing?

## SessionProvider / PersistentSessionProvider
**Path/Symbol:** `src/cuga/backend/knowledge/session_provider.py` (`SessionProvider` :113-216; `PersistentSessionProvider` :219-284; `_deep_merge` :103-110; `session_prefix`/`agent_prefix` :29-38; `check_session_access` :140-155; `collect_expired_sessions` :166-181).
**Signature:** `patch_session_overrides(thread_id, patch, user_id="", tenant_id="") -> SessionKnowledgeState`; `check_session_access(thread_id, user_id, tenant_id) -> bool`; `session_prefix(thread_id) -> "sess_<16-char-id>/"`.
**Data Shape:** `SessionKnowledgeState{thread_id, user_id, tenant_id, filter_id?, filenames[], overrides{}, created_at}`; `AgentKnowledgeState` keyed `f"{agent_id}:{config_version}"`. Persistence = whole-state JSON dump on EVERY mutation.

### Decisive source
```python
# :103-110 — recursive dict merge; non-dict on either side = wholesale replace
def _deep_merge(base: dict, patch: dict) -> dict:
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
    return base

# :149-155 — ownership enforced ONLY when BOTH sides know the id (empty = wildcard)
if state.user_id and user_id and state.user_id != user_id:
    return False

# :31-33 — short thread_ids padded so prefixes are never empty
tid = thread_id.ljust(_SESSION_PREFIX_ID_LEN, "0")[:_SESSION_PREFIX_ID_LEN]
```

**Flow:** routes MUST mutate only through provider methods (`save()` is in-memory in the base; the persistent subclass overrides every mutator to call `_persist()` after `super()`) → patch creates missing sessions WITH the caller's user/tenant stamped (`test_patch_creates_owned_session`) → deep merge means two sequential PATCHes on different keys (or nested keys) both survive — the exact regression the sibling tests pin → expiry collection returns-but-does-not-delete sessions older than max age, skipping unparseable timestamps.
**Invariant:** Never write the JSON file directly; write-through lives in overridden mutators, so a new mutation method that forgets `super()+_persist()` silently loses durability (the docstring's rule exists because of this). Ownership check treats absent owner OR absent caller as allow (bootstrap), enforced only when both present. Prefixes are storage-layout contracts: 16-char zero-padded session ids, `agent_<id>_<version>/` — changing them orphans existing documents.
**Probe:** direct tests `tests/unit/test_session_knowledge.py::TestSequentialNestedPatches::test_sequential_nested_patches_preserve_siblings` (:124), `::test_patch_creates_owned_session` (:107), `::TestDeepMerge::test_overwrite_dict_with_non_dict` (:32), `::TestPrefixHelpers::test_session_prefix_short_id_padded` (:203), `::TestPersistentSessionProvider::test_load_on_init` (:246), `::test_patch_forwards_ownership` (:233), `::test_no_double_write` (:258).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "SessionProvider PersistentSessionProvider patch_session_overrides _deep_merge check_session_access", limit: 10 });
```

## Verdict
Adopt deep-merge patch semantics with ownership stamping at create-via-patch, write-through via mutator overrides only, TTL collect-separately-from-delete, and fixed-width storage prefixes. Adapt state fields and persistence format to your backend. Omit the legacy `filter_id` field unless you have equivalent pre-filter history.

<!-- capsule-v2 -->
# Per-agent draft locking + secret redaction — how do you serialize concurrent section PATCHes to the same agent draft and keep secret field names consistent across GET/PATCH/env-presets?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** The manage UI fires concurrent autosave PATCHes to different draft sections (knowledge, tools, llm) — how does a per-agent lock stop read-modify-write interleaving from silently reverting a section, and how is "is this field a secret" decided in ONE place?

## Per-agent non-reentrant draft lock + single secret-name rule
**Path/Symbol:** `src/cuga/backend/server/manage_routes/helpers.py:214-244` (`AGENT_DRAFT_LOCKS`, `agent_draft_lock`, `load_and_patch_draft`, `save_draft_section_unlocked`), `:75-103` (`_SECRET_FIELD_SUBSTRINGS`, `is_secret_field_name`, `redact_secrets_in_config`), `:106-174` (`merge_feature_flags_defaults`), `:176-195` (`merge_mcp_yaml_into_config`), `:33-72` (`extract_agent_feature_overrides`).
**Signature:** `agent_draft_lock(agent_id) -> asyncio.Lock` (get-or-create, on-demand so no import-time event-loop dependency); `load_and_patch_draft(agent_id, section, value) -> dict` (locked load-modify-write); `save_draft_section_unlocked(agent_id, section, value) -> dict` (lock-free — ONLY when caller already holds the lock); `is_secret_field_name(name) -> bool`; `redact_secrets_in_config(config) -> None` (in-place, recursive).
**Data Shape:** `_SECRET_FIELD_SUBSTRINGS = ("KEY","TOKEN","SECRET","PASSWORD")` — "KEY" covers APIKEY + API_KEY both. `redact_secrets_in_config` walks nested dicts AND list items (a `{"tools":[{"api_key":"..."}]}` shape would otherwise leak a nested secret).

### Decisive source
```python
# helpers.py:198-213 — the interleaving this lock prevents
#   PATCH knowledge: load(draft_v0) → set knowledge=watsonx → save(v0+watsonx)
#   PATCH tools:     load(draft_v0) → set tools=new        → save(v0+tools) ← knowledge LOST
# asyncio.Lock is NON-reentrant — callers that already hold it MUST use *_unlocked.
AGENT_DRAFT_LOCKS: dict[str, asyncio.Lock] = {}
def agent_draft_lock(agent_id: str) -> asyncio.Lock:
    lock = AGENT_DRAFT_LOCKS.get(agent_id)
    if lock is None:
        lock = asyncio.Lock(); AGENT_DRAFT_LOCKS[agent_id] = lock
    return lock
```

**Flow:** `load_and_patch_draft` acquires the per-agent lock, loads the full draft, sets one section, saves — serializing concurrent cross-section PATCHes so neither reverts the other. The `patch_draft_knowledge` handler also acquires this lock for a WIDER critical section (engine apply + draft save together) so the live engine and persisted draft can't desync if a PATCH is aborted between them. `is_secret_field_name` is the single rule used by the env-presets endpoint, the GET-redactor, and the PATCH-preserver so they can't drift when a sixth secret substring gets added. `merge_feature_flags_defaults` fills `config.feature_flags` from stored `advanced_features` first, then global settings (per-agent demo/publish state must reflect correctly). `merge_mcp_yaml_into_config` backfills `command/args/transport/description/env` for MCP tools from the managed MCP YAML when the tool entry only has a name.

**Invariant:** The per-agent lock is the ONLY thing preventing cross-section draft clobbering — and it's non-reentrant, so any helper that already holds it must call the `_unlocked` variant or deadlock. Secrets are identified by name-substring in exactly one function so every redaction site agrees. Redaction recurses into lists, not just dicts.

**Probe:** `tests/unit/test_knowledge_draft_lmw_race.py:25` (`test_concurrent_cross_section_patches_preserve_all_sections`), `:70` (`test_lmw_lock_holds_under_repeated_contention`), `:106` (`test_per_agent_locks_do_not_serialize_different_agents`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "agent_draft_lock load_and_patch_draft is_secret_field_name redact_secrets_in_config merge_feature_flags_defaults", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the per-agent non-reentrant draft lock with on-demand creation and the `_unlocked`-variant discipline, plus the single secret-name-substring rule with list-recursing redaction. Adapt the secret substrings to your credential naming. Omit the feature-flags/MCP-YAML merge helpers if you don't have that manage surface. Direct-test coverage is strong for the race; redaction/merge are exercised via the manage API integration suite.

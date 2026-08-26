<!-- capsule-v2 -->
# Per-key DB config store — how do runtime-mutable settings persist while env-seeded defaults never override persisted values?

**Source:** open-webui "Open WebUI License" `main@01f4282f1ffe0d6212f58d3afbeae21fffd0c4be`; Codebase Memory `open-webui`. **Question:** How does app config persist to DB while env-seeded defaults never clobber persisted values, and which keys stay ephemeral?

## Config table + DEFAULTS dict
**Path/Symbol:** `backend/open_webui/models/config.py:Config` (lines 99-366) and `backend/open_webui/config.py:seed_registered_defaults / DEFAULT_CONFIG / Config.configure` (lines 40-43, 2788+, 3189-3193).
**Signature:** `async def get(key, default=None)` · `async def get_many(*keys) -> dict` · `async def upsert(updates: dict)` · `async def seed_defaults(defaults: dict)`.
**Data Shape:** one row per dotted key (`key TEXT PK, value JSON, updated_at BIGINT`). `DEFAULTS` maps dotted keys -> env-derived values; persistence gated by classvars `PERSISTENT_ENABLED`, `OAUTH_PERSISTENT_ENABLED`.

### Decisive source
\`\`\`python
async def seed_registered_defaults():
    await Config.rename_prefix('rag.web', 'web')
    await Config.repair_flattened_dict_configs()
    await Config.seed_defaults(DEFAULT_CONFIG)

@classmethod
def persistent_enabled_for(cls, key: str) -> bool:
    if not cls.PERSISTENT_ENABLED:
        return False
    if key.startswith('oauth.') and not cls.OAUTH_PERSISTENT_ENABLED:
        return False
    return True

# in seed_defaults: "Insert keys that don't yet exist in the DB."
if key not in existing_keys:
    value = _json_value(value)
    db.add(Config(key=key, value=value, updated_at=now))
\`\`\`

(config.py tail binds them at import:)
\`\`\`python
Config.configure(
    defaults=DEFAULT_CONFIG,
    enable_persistent=ENABLE_PERSISTENT_CONFIG,
    enable_oauth_persistent=ENABLE_OAUTH_PERSISTENT_CONFIG,
)
\`\`\`

**Flow:** env vars → module constants → `DEFAULT_CONFIG` dotted dict → `Config.configure` at import → boot calls `seed_defaults` which inserts only missing keys → runtime reads via `get/get_many/get_namespace` fall back to `DEFAULTS` when a key is absent → writes go through `upsert` (persistent keys to DB rows, non-persistent keys back into `DEFAULTS`).
**Invariant:** after first seeding, DB values win over env defaults forever (env edits do NOT re-override); `oauth.*` keys remain in-memory unless `ENABLE_OAUTH_PERSISTENT_CONFIG=true`; disabling persistence makes every read/write hit `DEFAULTS` only.
**Probe:** no test runner exists at this HEAD (zero test files, no pytest config) — deterministic anchor executed: `grep -n "Insert keys that don't yet exist" backend/open_webui/models/config.py` hits line 240 (seed_defaults spans 238-261; insert-if-absent at 256-259), and `sed -n '40,43p' backend/open_webui/config.py` equals the excerpt above.

## Get live surrounding code
**Retrieve:**
\`\`\`ts
await mcp.codebase_memory.search_graph({ project: "open-webui", query: "config persistent database env variable override save value", limit: 10, fields: ["signature", "name", "file"] });
\`\`\`

## Verdict
Adopt the insert-if-absent seeding algebra and per-key row storage with namespace gating; adapt the dotted-key naming and JSON value coercion (`_json_value`) to your host store; omit the legacy migration shims (`rename_prefix('rag.web','web')`, `import_legacy_config_json`) unless you carry open-webui history. Coverage caveat: none recorded for these paths; direct tests absent repo-wide.

<!-- capsule-v2 -->
# py-single-row-settings-and-key-ladder — how are provider configs and API keys stored without a migration framework?

**Source:** meetily (MIT) `main@0281737d`; Codebase Memory `ext-meetily`. **Question:** What is the settings persistence contract — single-row identity, per-provider key columns, and the try-ALTER migration idiom a porter must reproduce?

## Singleton row + whitelisted key-column map
**Path/Symbol:** `backend/app/db.py:DatabaseManager.save_api_key/get_api_key` (:582-643); `_legacy_init_db` (:45-159); `schema_validator.py:_validate_table_schema` (:94-127).
**Signature:** `async def get_api_key(self, provider: str)` → returns `""` when unset (never None).
**Data Shape:** Both `settings` and `transcript_settings` are SINGLETON tables addressed by literal `id = '1'`. Provider→column maps are hardcoded whitelists (`openai→openaiApiKey`, `claude→anthropicApiKey`, `groq→groqApiKey`, `ollama→ollamaApiKey`; transcript side adds `localWhisper→whisperApiKey`, `deepgram`, `elevenLabs`). Column names enter SQL via f-string AFTER whitelist validation — the whitelist IS the injection guard.

### Decisive source
```python
provider_list = ["openai", "claude", "groq", "ollama"]
if provider not in provider_list:
    raise ValueError(f"Invalid provider: {provider}")
...
await conn.execute(f"UPDATE settings SET {api_key_name} = ? WHERE id = '1'", (api_key,))
```

**Flow:** save path = BEGIN → SELECT row → UPDATE or INSERT-with-defaults (first key save seeds defaults `'1','openai','gpt-4o-2024-11-20','large-v3'`) → commit/rollback. Schema evolution has NO migrations: `_legacy_init_db` wraps each new column in `try: ALTER TABLE ... ADD COLUMN / except sqlite3.OperationalError: pass`, and `SchemaValidator.validate_schema` re-checks expected-vs-`PRAGMA table_info` at every startup, adding missing columns automatically.
**Invariant:** `get_api_key` returning `""` (not raising) is the upstream contract cloud branches rely on (`if not api_key: raise ValueError(... ANTHROPIC_API_KEY ...)`) — keep the empty-string sentinel or you break the "key missing" UX path.
**Probe:** `grep -cF 'chunk_size = 30000' backend/app/transcript_processor.py` is P1; for this seam: `grep -cF "WHERE id = '1'" backend/app/db.py` → 5 occurrences (:561,:607,:641,:681,:728).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-meetily", query: "save_api_key anthropicApiKey provider_list", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt whitelist-before-fstring SQL construction and the ALTER-on-startup validator; adapt to your ORM/migrations; omit the seeded default model names. Direct tests absent — coverage caveat recorded.

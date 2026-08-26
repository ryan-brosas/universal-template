<!-- capsule-v2 -->
# Embedding service + env seeding — how do you pick an embedder with a dim you can TRUST before writing vectors, and which env vars may auto-seed themselves into the secret store?

**Source:** cuga-agent Apache-2.0 `main@5de53ade`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** Why does the embedder probe a real vector to learn its dimension (and when is the configured dim trusted instead), and what three filters decide whether an arbitrary env var becomes a persisted secret?

## Provider ladder + guarded auto-seed
**Path/Symbol:** `src/cuga/backend/storage/embedding/embedding_service.py` (`LOCAL_MODEL_DIMS` :13-19; `get_embedding_dimension` :42-55; `create_embedding_function` :58-96; `_create_local` :133-165), `src/cuga/backend/secrets/seed.py` (`_STATIC_ENV_SEED_MAP` :9-20; `_DYNAMIC_PATTERN` :22; `_SKIP_PREFIXES` :25-37; `seed_secrets_from_env` :81-116; `resolve_llm_api_key_ref` :128-153).
**Signature:** `create_embedding_function(provider=None, model=None, base_url=None, api_key=None, dim=None) -> tuple[Optional[callback], int]`; `seed_secrets_from_env() -> None`.
**Data Shape:** Returns `(embed_fn|None, dim)` — fn None means "no provider available" and callers must NOT write vectors. Local models run through fastembed with a module-level model cache keyed by model name; dim comes from a REAL `"probe"` embedding (`len(sample)`), not from a table.

### Decisive source
```python
# embedding_service.py:49-55 — configured_dim is trusted ONLY for custom endpoints
# (base_url set): local dims come from the known table, openai fixed 1536
if base_url and configured_dim: return configured_dim
if provider == "openai": return 1536
if provider == "local":  return LOCAL_MODEL_DIMS.get(model_name or "BAAI/bge-small-en-v1.5", 384)

# :149-151 — the table can lie about fine-tuned/quantized variants → measure once
sample = next(model.embed(["probe"]))
dim = len(sample)

# seed.py:22 — the dynamic filter is KEYWORD-shaped, not value-shaped:
_DYNAMIC_PATTERN = re.compile(r"(?:^|_)(KEY|SECRET|TOKEN|PASSWORD|PASSWD|PWD)(?:$|_)", re.I)

# seed.py:90-96 — vault mode: Vault is source of truth, DB seed skipped ENTIRELY;
# no CUGA_SECRET_KEY: no DB backend at all — both skips are silent by design
if _secrets_mode() == "vault": return
if not _fernet(): return

# :105-109 — existing slug NEVER overwritten (restarts must not rotate keys)
existing = await get_secret(slug)
if existing is not None: continue
await set_secret(slug, value, description=f"Auto-seeded from {env_var}", created_by="system")
```

**Flow:** config resolution (`storage.embedding.provider/model/dim/base_url/api_key`, defaults bge-small/384) → provider ladder local/openai/auto-with-openai-fallback-to-local → local path caches the fastembed model process-wide, honors `FASTEMBED_CACHE_PATH` + `HF_HUB_OFFLINE`, measures dim from a probe vector → caller persists only when `(fn, dim)` has a non-None fn. Seeding runs once at startup: static pin map first (GROQ/OPENAI/ANTHROPIC/GOOGLE/OPENROUTER/MINIMAX/RITS/WATSONX/AZURE/LITELLM), then dynamic scan of every non-empty env var matching the keyword pattern minus skip prefixes; each seeds as lowercase-hyphen slug.
**Invariant:** (1) Writing vectors with a WRONG declared dim corrupts the collection irrecoverably (schema froze the dim) — that's why local dims are measured, and why `create_embedding_function` returns None-fn instead of guessing. (2) The system must never seed ITS own infra vars: skip prefixes (`CUGA_`, `VAULT_`, `AWS_SESSION_`, `KUBERNETES_`, plus PATH/HOME/USER/SHELL/LANG/LC_/HOSTNAME) exist because the pattern alone would match e.g. `VAULT_TOKEN`. (3) Seed = insert-if-absent ONLY; rotation happens through the UI/store, never restart. (4) `resolve_llm_api_key_ref` matches provider hints LONGEST-FIRST ("azure-openai" beats "gpt") so `db://slug` references point at the right key.
**Probe:** No direct unit test for either file at this HEAD — seeding behavior is pinned transitively via the store contract (`secrets_store` imports in seed.py :88) and the resolver chain (`secret_resolver.py` consumes the same slugs); embedder cache resilience lives in `tests/unit/test_embedder_cache_resilience.py` (knowledge engine side). Coverage caveat: both files verified by whole-file source read.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "create_embedding_function get_embedding_dimension LOCAL_MODEL_DIMS seed_secrets_from_env _DYNAMIC_PATTERN resolve_llm_api_key_ref", limit: 10 });
```

## Verdict
Adopt probe-measured local dims (trust configured dim only for custom endpoints), None-fn-no-write failure shape, the three-filter seed gate (static pins / skip prefixes / keyword pattern), insert-if-absent semantics, and longest-first provider hint matching. Adapt model names/dims and slug formats to your host. Omit nothing from the skip-prefix list without re-checking it against your own infra var names.

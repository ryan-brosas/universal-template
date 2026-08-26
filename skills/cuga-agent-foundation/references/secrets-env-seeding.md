<!-- capsule-v2 -->
# Secrets env seeding — how do you auto-import API-key-shaped environment variables into a secrets store without hoovering internal infra vars?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** Which env vars qualify for auto-seed at startup, and what three filters keep infra/internal vars out?

## Static map + dynamic KEY/SECRET/TOKEN/PASSWORD pattern with prefix skips
**Path/Symbol:** `src/cuga/backend/secrets/seed.py:10-53` (`_STATIC_ENV_SEED_MAP`, `_DYNAMIC_PATTERN`, `_SKIP_PREFIXES`, `_build_seed_map`).
**Signature:** `_build_seed_map() -> dict[str, str]` (env var → store slug, slug = lowercased, underscores→dashes).
**Data Shape:** Static entries pin known provider keys to stable slugs (`OPENAI_API_KEY → openai-api-key`, `WATSONX_APIKEY → watsonx-api-key`, 10 providers). Dynamic candidates must have a non-empty value and match `(?:^|_)(KEY|SECRET|TOKEN|PASSWORD|PASSWD|PWD)(?:$|_)` case-insensitively.

### Decisive source
```python
# seed.py:21-31
_SKIP_PREFIXES = (
    "CUGA_", "VAULT_", "AWS_SESSION_", "KUBERNETES_",
    "HOSTNAME", "PATH", "HOME", "USER", "SHELL", "LANG", "LC_",
)
# _build_dynamic_seed_map: skip empty values, skip static-map members,
# skip _SKIP_PREFIXES, then require _DYNAMIC_PATTERN.search(env_var)
```
The three filters are the porting contract: (1) static-map membership — pinned slugs must not be recomputed from the dynamic rule; (2) skip-prefixes — the app's own config namespace (`CUGA_*`), the secret backends' own credentials (`VAULT_*`, `AWS_SESSION_TOKEN`), and K8s/system vars are infrastructure, not user secrets; (3) the keyword pattern — a var must explicitly carry KEY/SECRET/TOKEN/PASSWORD/PASSWD/PWD as a delimited segment. `AWS_SESSION_TOKEN` shows why order matters: it matches the dynamic pattern but is excluded by `AWS_SESSION_` prefix before seeding could create a bogus entry.

**Flow:** startup seeding reads the merged map and writes each `{slug: value}` into the DB secrets store so LLM/MCP auth resolves through the normal ladder instead of requiring manual registration.
**Invariant:** Never seed a variable that the system itself needs to operate (backends' own creds, app namespace); dynamic seeding only ever ADDS candidate-looking vars, never overrides static pins.

**Probe:** No dedicated unit test file for seed filtering in tests/unit — coverage caveat: the static map + filters live entirely in this module; verify by reading source when porting.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "seed secrets env build_seed_map", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the static-pin + dynamic-pattern + prefix-skip triple filter and slug normalization. Adapt the static map to your providers. Omit DB seeding if your resolver only reads env.

<!-- capsule-v2 -->
# Config precedence ladder — which surface may carry which secret, and who wins

**Source:** linkedin-mcp-server Apache-2.0 `main@0cd1e5fb2907`; Codebase Memory `linkedin-mcp-server`. **Question:** How do defaults, environment variables, and CLI flags compose into one validated config — and why does the SAME proxy setting have opposite credential rules per surface?

## load_config / load_from_env / load_from_args
**Path/Symbol:** `linkedin_mcp_server/config/loaders.py` — `load_config` (:854-882), `load_from_env` (:218-436), `load_from_args` (:439-851), `credential_free_url` (:62-89), `_env` (:177-202).
**Signature:** `load_config() -> AppConfig`; `load_from_env(config) -> AppConfig`; `load_from_args(config) -> AppConfig`; `credential_free_url(value: str) -> str`.
**Data Shape:** One mutable `AppConfig` threaded through the ladder; env booleans via TRUTHY/FALSY string sets; numeric env vars re-validated inline (`ConfigurationError` on bad shape) with final clamping deferred to `AppConfig.validate()`.

### Decisive source
```python
# loaders.py :854-881 — the whole precedence contract
config = AppConfig()                       # 3. defaults (lowest)
config.is_interactive = is_interactive_environment()
config = load_from_env(config)             # 2. environment
config = load_from_args(config)            # 1. command line (highest)
config.validate()

# :71-89 — argv is world-readable, so it may never carry a proxy password
has_credentials = bool(parsed.username or parsed.password) or (
    "@" in unquote(parsed.hostname or "")   # "user%3Apass%40host" counts too
)
if has_credentials:
    raise argparse.ArgumentTypeError(
        "must not contain credentials. Pass the bare scheme://host:port "
        "here and supply the password via the PROXY_PASSWORD environment "
        "variable, so it is not exposed in the process list.")

# :199-202 — MCPB placeholder left by a host is treated as unset; no strip()
value = os.environ.get(key)
if not value or value == _MCPB_PLACEHOLDERS.get(key):
    return None
return value
```
**Flow:** dotenv loaded at import → defaults → env overrides (invalid shapes refuse loudly) → argv overrides → single `validate()`. Env PROXY_SERVER MAY embed credentials (:371-374: environment is not world-readable); the CLI flag NEVER may, and no `--proxy-password` flag exists at all. An env var equal to its exact `${user_config.X}` MCPB placeholder is skipped as unset with a warning naming the keys.
**Invariant:** Precedence is args > env > defaults, and secret policy follows the EXPOSURE SURFACE, not the setting. Placeholder detection uses one exact literal per variable — never a pattern — because a pattern would swallow a real password that happens to match the shape; and `_env` never strips, because a password may begin/end with a space.
**Probe:** `tests/test_config.py` — `test_args_override_env` (:1103-1111) pins args>env for PROXY_SERVER; `test_load_from_env...` (:1075-1081) pins env-carried credentials splitting into server+password; `test_cli_rejects_embedded_credentials` (:1113+) pins the argv refusal.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linkedin-mcp-server", query: "load_config precedence defaults environment arguments validate", limit: 8, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-step ladder plus exposure-based credential policy and exact-literal placeholder skipping for any server configurable from both shell and hosted-bundle hosts. Adapt the variable table and validation split (inline vs validate()). Omit the MCPB/manifest specifics unless targeting Claude-Desktop-style bundles. Coverage caveat: none — loaders.py fully indexed (no_recorded_issue).

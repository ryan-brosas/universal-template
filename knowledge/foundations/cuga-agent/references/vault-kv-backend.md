<!-- capsule-v2 -->
# Vault KV backend — how do you support KV v1 AND v2, kubernetes AND token auth, and path#field addressing against hvac without letting any of it raise?

**Source:** cuga-agent Apache-2.0 `main@5de53ade`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** A porter wiring HashiCorp Vault must know where the v1/v2 API divergence is handled (hvac does NOT normalize it), how the mount/path split works, and why unset kv_version means v2-only.

## Path resolution + version-split client
**Path/Symbol:** `src/cuga/backend/secrets/backends/vault_backend.py` (`_vault_addr_and_auth` :28-36; `_get_client` :39-108; `_parse_vault_path` :111-115; `_normalize_kv_v2_data_prefix` :118-121; `_split_mount_and_path` :124-137; `_resolve_vault_path` :160-198; `VaultBackend.get` :293-354).
**Signature:** `_resolve_vault_path(secret_id, vault_secret_path, mount_point, kv_version) -> tuple[str, str, str]` = `(mount_point, crud_secret_path, list_prefix)`; `get(path, *, field=None, ...) -> str | None`.
**Data Shape:** settings/env ladder on every knob: `vault_addr`, `vault_auth_method` (`token`|`kubernetes`, else unsupported→None), `vault_mount` (default `secret`), `vault_kv_version` (`""`=v2), `vault_secret_path` base, TLS via `vault_cacert`/`VAULT_CACERT`/skip flags with stringy truthiness ("1","true","yes","on") accepted. Addressing: `path#field` picks one key from the payload.

### Decisive source
```python
# :118-121 — hvac KV v2 prepends data/ itself; strip it from user paths for v2 ONLY
def _normalize_kv_v2_data_prefix(rest: str) -> str:
    return rest[len("data/"):] if rest.startswith("data/") else rest
# v1 may legitimately use "data/" as a REAL path segment — never strip there

# :337-344 — unset kv_version defaults to v2 and MUST NOT fall back to v1:
# that hits /v1/{mount}/{path} which fails on versioned KV mounts with
# "Invalid path..." warnings noise
resp = client.secrets.kv.v2.read_secret_version(path=secret_path, mount_point=mount_point)
data = (resp or {}).get("data", {}) or {}
payload = data.get("data", data)     # v2 double-wraps: {data:{data:{...}}}

# :185-194 — explicit base path pins the mount (never guess mount from path)
if (vault_secret_path or "").strip():
    merged = _merge_vault_secret_base(sid, vault_secret_path)
    crud_path = _normalize_kv_v2_data_prefix(merged) if kv != "1" else merged
    return mp, crud_path, list_prefix   # mp is the CONFIGURED mount, always

# :62-90 — kubernetes auth: role REQUIRED else None; JWT from configurable path
# defaulting to the in-pod serviceaccount token; login then VERIFY is_authenticated()
client.auth.kubernetes.login(role=role, jwt=jwt, mount_point=mount)
if not client.is_authenticated(): return None
```

**Flow:** lazy singleton client (`_client_or_none`) → `_get_client` returns None on ANY failure (missing hvac import, no addr, unsupported auth, unreadable JWT, failed login, generic exception — all debug-logged). Resolution: parse `#field` off the id → strip leading mount if user included it (avoid double-prepending) → merge bare ids under the configured base path → v2-normalize `data/` → split mount only when no base path configured (first segment = mount). Read: version-split API call → unwrap v2's `{data:{data:…}}` vs v1's `{data:…}` → field pick order: `path#field` > `field` kwarg > `"value"` key > first payload value. Delete: v1 `delete_secret` vs v2 `delete_metadata_and_all_versions` (destroys history).
**Invariant:** (1) EVERY public method returns None/False/[ ] on failure — Vault being down must degrade to the next backend in the resolver chain, never break an agent turn. (2) The v1/v2 branch is decided by string compare against `str(kv_version)` consistently — keep treating `""` as v2, adding v1 fallback re-introduces the Invalid-path warning bug. (3) Mount guessing from path happens ONLY when no explicit base path is set; with a base, the configured mount always wins. (4) `available()` caches the client (including its None) on the instance.
**Probe:** No direct unit tests at this HEAD (Vault requires a live server); vault-mode config publishing is exercised by `tests/integration/test_llm_config_publish.py` (:63 `_vault_settings_stub`, :80/:107 publish-in-vault-mode tests) and the resolver-level contract (None-not-raise) by construction in `secret_resolver._active_backends`. Coverage caveat: path-resolution helpers are pure but untested directly.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "VaultBackend _resolve_vault_path _split_mount_and_path _normalize_kv_v2_data_prefix kubernetes login", limit: 10 });
```

## Verdict
Adopt the resolve-to-(mount, path, list-prefix) triple, v2-only-by-default with explicit `!= "1"` gating, the double-wrap unwrap, the never-raise degradation, and the k8s-JWT/token auth pair. Adapt default mount/knob names to your host. Omit the AWS-style JSON-field parsing here (that lives in AwsBackend) and do NOT port the v1 fallback-on-empty — it's documented as a deliberate non-feature.

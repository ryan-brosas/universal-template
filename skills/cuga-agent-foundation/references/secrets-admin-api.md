<!-- capsule-v2 -->
# Secrets admin API — how do you expose a secrets CRUD surface that writes to Vault or the DB by mode, enforces creator-only ownership, and masks values on resolve?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** The manage UI needs to list/create/update/delete secret overrides and debug-resolve a ref — how does the route pick Vault vs DB by mode, enforce that only the creator can mutate a secret, and return a masked value instead of the plaintext?

## Mode-routed CRUD + creator-only ownership + masked resolve
**Path/Symbol:** `src/cuga/backend/server/secrets_routes.py:44-107` (`list_secrets`), `:147-189` (`create_secret`), `:192-238` (`update_secret`), `:252-297` (`delete_secret`), `:300-316` (`resolve_secret_debug`), helpers `_secrets_mode` `:125-132`, `_vault_write` `:135-144`, `_vault_delete` `:241-249`.
**Signature:** Router prefix `/api/secrets`, all routes `Depends(require_auth)`. `create_secret(body: SecretCreate, current_user) -> {"ref": str, "id": str}`; `resolve_secret_debug(body: {"ref"|"name": str}) -> {"resolved": bool, "masked": str|None}`.
**Data Shape:** `SecretCreate` = `{id, value, description?, tags?, agent_id?, version?}`; `SecretUpdate` = `{value, description?, tags?, agent_id?, version?}`. Default user id `"local"`. Scope defaults `agent_id="*"`, `version="*"`. Ref strings: `vault://secret/{id}#value` (vault mode) vs `db://{id}` (db mode).

### Decisive source
```python
# secrets_routes.py:153-179 — mode-routed write with creator-only guard
mode = _secrets_mode()
if mode == "vault":
    ok = _vault_write(body.id, body.value, description=body.description)
    if not ok:
        raise HTTPException(status_code=503, detail="Vault unavailable or write failed...")
    return {"ref": f"vault://secret/{body.id}#value", "id": body.id}
meta = await secrets_store.get_secret_metadata(body.id)
if meta:
    creator = meta.get("created_by") or ""
    if creator and _user_id(current_user) != creator:
        raise HTTPException(status_code=403, detail="Only the creator can update this secret")
await secrets_store.set_secret(body.id, body.value, ..., agent_id=body.agent_id or "*",
                               version=body.version or "*", created_by=_user_id(current_user))
```

**Flow:** `list_secrets` merges three sources: DB overrides, Vault items (mode=vault, keys not already in DB), and env-var-backed seeds (mode=local or force_env, env var set + slug not already present) — each tagged with `source` (db/vault/env) and `agent_id` (`*` for vault/env). Create/update/delete: in vault mode write/delete through Vault (503 if unavailable); in db mode, fetch metadata with the same scope, enforce creator-only (403 if `created_by` set and differs from the authenticated user), then `set_secret`/`delete_secret` scoped to `agent_id`/`version`. `resolve_secret_debug` calls `resolve_secret(ref)` and returns a masked value: `val[:4] + "••••" + (val[-2] if len(val)>6 else "")`, or `"••••"` for len<=4, or `{"resolved": False}` when None.

**Invariant:** Secrets are never returned in plaintext — list returns metadata only (no values), resolve returns a masked prefix. Creator-only ownership is enforced on every mutation (create/update/delete) so one operator can't overwrite another's secret. The vault-mode write refuses loudly (503) rather than silently falling back to DB, so an operator who configured Vault knows when it's down.

**Probe:** No direct unit test file for `secrets_routes.py` at HEAD (route-level; `resolve_secret` itself is covered by the secrets-resolution-ladder capsule's tests). The masked-resolve and creator-ownership logic is exercised via the manage API integration suite. State this coverage caveat.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "resolve_secret_debug create_secret _vault_write _secrets_mode is_secret_field_name", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the mode-routed CRUD (vault vs db), the creator-only ownership guard, the three-source list merge (db+vault+env), and the masked resolve. Adapt the masked-prefix format and auth dependency to your API. Omit the FastAPI router shape if not building the manage UI. Coverage caveat: no direct unit test at HEAD — verify the ownership/mask logic against your own route tests.

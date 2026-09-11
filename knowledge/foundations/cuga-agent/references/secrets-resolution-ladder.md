<!-- capsule-v2 -->
# Secrets resolution ladder — how do you resolve `vault://`/`db://`/`aws://`/`env://` refs (and bare env names) across optional backends without failing a run?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** How is a secret reference parsed and which backend wins, given that Vault/AWS/DB may all be unavailable at runtime?

## Scheme parse → scheme-first pass → any-backend pass → None
**Path/Symbol:** `src/cuga/backend/secrets/secret_resolver.py:8-30` (`parse_ref`), `:41-90` (`_active_backends`), `:93-131` (`resolve_secret`).
**Signature:** `parse_ref(ref: str) -> Tuple[str, str]`; `resolve_secret(ref: str, *, agent_id=None, tenant_id=None, instance_id=None) -> str | None`.
**Data Shape:** Schemes: explicit `vault://`, `db://`, `aws://`, `env://`; a bare string matching `^[A-Z][A-Z0-9_]*$` is treated as an env var name; everything else is `"plain"` and returned verbatim. `db://` path truncates at first `/` or `#`.

### Decisive source
```python
# secret_resolver.py:113-131 — two passes over the backend chain
backends = _active_backends()
for backend in backends:
    if getattr(backend, "scheme", None) == scheme:
        try:
            val = backend.get(path, agent_id=..., tenant_id=..., instance_id=...)
            if val is not None:
                return val
        except Exception as e:
            logger.debug("Secret backend {} get failed: {}", backend.scheme, e)
for backend in backends:   # second pass: no scheme filter
    ...
return None                # never raises
```
`_active_backends` builds an availability-filtered chain: `force_env` ⇒ `[EnvBackend]` only; vault mode ⇒ `[VaultBackend?, EnvBackend]`; local mode probes Vault, AWS, EnvOverride, Db — each wrapped in try/except with `.available()` checks — then ALWAYS appends EnvBackend as the terminal fallback. Backend get failures are debug-logged and skipped; the resolver returns `None` rather than raising.

**Flow:** ref → parse_ref (scheme inference incl. the ALL-CAPS env-name heuristic) → plain? return as-is → build chain per settings → pass 1 restricted to matching scheme → pass 2 unrestricted → `None`. Callers treat None as "unresolved" (e.g. mcp_manager auth values, llm/models.py API-key lookup).
**Invariant:** Resolution must never raise into a request path; unresolvable ≠ error. The env fallback is unconditional so a misconfigured Vault degrades to env vars instead of bricking LLM/tool auth.

**Probe:** No dedicated unit test for `resolve_secret` itself in tests/unit (grep found only indirect coverage via llm/mcp tests) — coverage caveat: verify behavior by reading this file directly when porting; backends' `.available()` gating is the contract.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "resolve_secret parse_ref active backends", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the scheme-parse + two-pass ladder + never-raise contract and the ALL-CAPS-bare-string heuristic. Adapt backend set to your infra. Omit db:// field-truncation if your DB store has no composite paths.

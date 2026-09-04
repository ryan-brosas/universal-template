<!-- capsule-v2 -->
# Descriptor trust — how does a client trust a discovered daemon endpoint before sending a bearer token?

**Source:** linkedin-mcp-server Apache-2.0 `main@cfcd9c9a`; Codebase Memory `linkedin-mcp-server`. **Question:** What makes daemon discovery safe on a multi-user machine, and how are token/config/instance mismatches refused?

## Loopback-checked endpoints + keyed fingerprint + instance-named tokens
**Path/Symbol:** `linkedin_mcp_server/daemon_descriptor.py` (:1-1010; `config_fingerprint` :528, `token_path` :431, `new_token` :467).
**Signature:** `config_fingerprint(config: AppConfig, *, key: str) -> str`; `token_path(auth_root: Path, instance_id: str) -> Path`; `new_token() -> str` (fresh per daemon start, never reused).
**Data Shape:** Descriptor carries endpoint address (loopback-checked before any token moves), exact profile-path comparison, `config_fingerprint`, `package_version`, `protocol_version`, `instance_id`, `token_sha256`. The TOKEN itself lives BESIDE the descriptor as `token-<instance_id>` — named so a descriptor and a foreign token can never be paired across generations.

### Decisive source
```text
- Nothing here is taken on trust: the endpoint is checked to be loopback
  BEFORE the token goes anywhere; profile path compared exactly;
  configuration compared through a KEYED fingerprint — ``proxy_password``
  and secrets never enter the digest, but the key binds the fingerprint to
  this server identity, so a process speaking from a stale descriptor
  cannot pass for the current daemon.
- token_sha256 compared with hmac.compare_digest, which refuses a
  non-ASCII/equal-time shortcut.
- protocol_version enforced by EQUALITY (wire contract: disagreement means
  two processes cannot talk) — unlike package_version skew policy.
```
**Flow:** find descriptor → verify loopback → compare profile path exactly → recompute+compare keyed config fingerprint → read instance-named token file → digest-compare → attach with fresh bearer token.
**Invariant:** Publish trust parameters, don't assume them; verify identity-scoped fingerprints on EVERY bind. Token files are named per instance so next-generation tokens read as mismatch, not corruption.
**Probe:** `tests/test_daemon_descriptor.py` (995L) pins fingerprint mismatch rejections and loopback checks.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linkedin-mcp-server", query: "daemon_descriptor config_fingerprint token_path loopback", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt loopback-gating + keyed fingerprints + instance-named secrets for local service discovery. Adapt field names. Omit MCP-specific protocol versioning details beyond the equality-vs-skew distinction.

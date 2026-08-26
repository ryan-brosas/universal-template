<!-- capsule-v2 -->
# Two-phase artifact upload + verified commit — how do you let a tool push content too big for a tool call without trusting the uploader?

**Source:** pipeshub-ai Apache-2.0 `main@4a02110dd9a7a644d8ba7a5ccd295c58a3c3628f`; Codebase Memory `pipeshub-ai`. **Question:** What makes an upload grant safe — single-use? server-derived keys? re-verification at commit?

## Grant → direct PUT → re-download, re-hash, THEN bump
**Path/Symbol:** `backend/python/app/services/artifact_registry/signed_urls.py:SignedUrlBroker.get_upload_grant/pop_grant/gc_expired_grants/_PENDING_GRANTS` (L38–121); commit half `services/artifact_registry/registry.py:commit_version` (L301–324).
**Signature:** `get_upload_grant(*, org_id, user_id, artifact_id, document_id, declared_size, declared_sha256, mime_type, ttl_s=600) -> UploadGrant`; `pop_grant(grant_id, *, org_id, user_id) -> dict`; `commit_version(*, actor, grant_id) -> tuple[ArtifactVersion, ArtifactMetadata]`.
**Data Shape:** `_PENDING_GRANTS[grant_id] = {artifact_id, document_id, org_id, user_id, declared_size, declared_sha256, mime_type, expires_at_epoch_ms}`; `UploadGrant` carries `upload_url` (server-derived object key — caller never supplies a path), grant id, and its own declaration echo.

### Decisive source
```python
# Security posture (module docstring): every method takes an ALREADY-AUTHORIZED
# record (AccessPolicy ran upstream); grants are short-lived (600s default),
# SINGLE-USE (popped on commit or expiry), bound to a server-derived object key.
if declared_size > self._max_bytes:
    raise GrantVerificationError(...)

def pop_grant(grant_id, *, org_id, user_id):
    grant = _PENDING_GRANTS.pop(grant_id, None)          # pop FIRST: consume-once
    if grant is None:
        raise GrantExpiredError("Unknown or already-consumed grant")   # guess == expired
    if grant["org_id"] != org_id or grant["user_id"] != user_id:
        raise GrantExpiredError("...does not belong to this actor")    # wrong actor == expired
    if grant["expires_at"] < now_ms():
        raise GrantExpiredError("...has expired")
    return grant

# registry.commit_version — NEVER trust the client's PUT to have matched what
# it declared ("a compromised/buggy uploader cannot silently smuggle oversized
# or substituted content past the declared metadata"):
content = await fetch_blob_bytes(org_id=..., storage_document_id=grant["document_id"])
actual = compute_content_hash(content)
if len(content) != grant["declared_size"] or actual != grant["declared_sha256"]:
    raise GrantVerificationError("... size/hash mismatch — refusing to commit this version.")
return await self._versions.add_version(actor=actor, artifact_id=grant["artifact_id"],
                                        content=content, mime_type=grant["mime_type"])
```
Known-limitation honesty: `_PENDING_GRANTS` is process-local in-memory — fine for a 10-minute grant, doesn't survive restart or fan out across replicas; documented as a follow-up with "a Redis-backed store would be a drop-in replacement behind the same three methods" rather than solved here.

**Flow:** authorize → issue grant (size-cap pre-check, direct-PUT URL from blob store, TTL clock) → client PUTs bytes directly → commit: pop grant (ownership+expiry verified by the SAME error type so probing costs the same as guessing) → RE-DOWNLOAD the stored bytes → re-hash → compare against the grant's declaration → mismatch raises `GrantVerificationError`, match flows into the standard `add_version` (which dedupes/conflict-checks as usual). Expired never-committed grants are swept by `gc_expired_grants()` from the periodic cleanup loop.
**Invariant:** (1) Single-use via pop-first — a replayed grant id finds nothing. (2) Wrong org/user and unknown/expired are the SAME exception class, so error messages leak nothing about which ids exist. (3) Commit verification reads the ACTUAL stored bytes, not client claims. (4) The broker never checks permissions itself — single responsibility; authorization happened before grant issuance. (5) In-memory grants are a documented MVP trade, replaceable behind the same three methods.
**Probe:** `tests/unit/services/artifact_registry/test_signed_urls.py` (133L): issues_grant_within_size_cap :41; rejects_declared_size_over_cap :53; consumes_grant_exactly_once :64; unknown_grant_id_raises_expired :77; grant_for_wrong_actor_raises_expired :82; expired_grant_raises :96; removes_only_expired_grants :112.

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph --project pipeshub-ai --query "SignedUrlBroker get_upload_grant pop_grant commit_version GrantVerificationError" --detail ids
```

## Verdict
Adopt grant→PUT→verify-commit with pop-first single-use, uniform expired-error taxonomy, server-derived keys, and post-upload re-hash; keep the broker authorization-free. Adapt storage backend and TTL defaults to the host; swap the in-memory grant table for Redis when multi-replica. Omit Node.js URL signing.

<!-- capsule-v2 -->
# Deployment affinity (user-key / session pins) — how do you pin a caller to one deployment with first-writer-wins claims that survive Redis blips?

**Source:** litellm (MIT), `litellm_internal_staging@f005afa1`; Codebase Memory `ext-litellm`. **Question:** cache-backed stickiness keyed by API-key hash and session id without cross-caller pin theft.

## deployment-affinity-claim-pins
**Path/Symbol:** `litellm/router_utils/pre_call_checks/deployment_affinity_check.py:DeploymentAffinityCheck` (`_CLAIM_PIN_SCRIPT` :63-73, `_set_local_pin` :336-342, `_claim_pin` :344-385, `_claim_pin_in_memory` :387-402, `async_filter_deployments` :415-538, `async_pre_call_deployment_hook` :540-679).
**Signature:** `_claim_pin(cache_key: str, pin_value: DeploymentAffinityCacheValue, ttl_seconds: int) -> str | None`; keys `deployment_affinity:v1:{model_group}:{sha256(user_key)}` and `...:session:{model_group}:{hash|unscoped}:{session_id}`.
**Data Shape:** stored value `{"model_id": str}` (readers also accept legacy bare-string values via `_pinned_model_id`). User key = proxy's `metadata.user_api_key_hash` — the OpenAI `user` param is deliberately NOT used (:258-260 note).

### Decisive source
```lua
local current = redis.call('GET', KEYS[1])
if current == false then
  redis.call('SET', KEYS[1], ARGV[1], 'EX', ARGV[2])
  return ARGV[1]
end
if current == ARGV[1] then
  redis.call('EXPIRE', KEYS[1], ARGV[2])
end
return current
```
(_CLAIM_PIN_SCRIPT :63-73) — first-writer-wins; re-claim by the CURRENT owner refreshes TTL (keepalive), so `session_affinity_ttl_seconds` bounds IDLE time, never total session length.

**Flow:** filter phase priority: (1) `previous_response_id` continuity pin [highest]; (2) session-id pin; (3) user-key pin. A hit returns `[that deployment]`, but only if it's in today's healthy set (`_find_deployment_by_model_id` else fall through to normal routing — stale pins degrade, never block). Write phase runs in `async_pre_call_deployment_hook` — deliberately PRE-call, not in the background logging worker, so the very next request already sees the pin. Per-model-group flags come from `model_group_affinity_config[group]` membership, falling back to global instance flags; unknown flags warn once at schema level (`warn_on_unknown_model_group_affinity_flags`, VALID set includes encrypted_content_affinity owned by the sibling check).
**Invariant:** (1) Redis claim failure degrades to the pod-local check-and-set (synchronous on the event loop ⇒ atomic) instead of propagating — an escaping error would leave the session unpinned and reshuffle every turn for the outage; (2) local pin writes go through `_set_local_pin` which DELETES then re-sets: plain sets keep a live key's original expiry (`allow_ttl_override`), making TTL lies possible; this is "the one owner of authoritative local pin writes"; (3) session pins are scoped by hashed caller key (`"unscoped"` for direct Router use) so two callers sharing a client-supplied session_id cannot read or steer each other's pin; (4) sha256-hex-looking inputs are kept as-is to avoid double-hashing proxy-provided hashes; (5) model-map scoping requires the derived key to be STABLE across all healthy deployments (`_get_stable_model_map_key_from_deployments`) — Azure deployment names without base_model return None and disable scoping rather than pinning wrongly.
**Probe:** `tests/test_litellm/router_utils/pre_call_checks/test_session_id_affinity.py::test_claim_pin_uses_redis_attached_after_construction` (:446) + `test_deployment_affinity_check.py::test_cache_key_does_not_double_hash_user_api_key_hash` (:664); both suites GREEN (45 passed) at pin.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-litellm", query: "DeploymentAffinityCheck _claim_pin", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the Lua get-or-set-or-refresh claim shape and delete-before-set local writes; adapt key grammar/hash choice; omit per-group flag config if you only need global toggles.

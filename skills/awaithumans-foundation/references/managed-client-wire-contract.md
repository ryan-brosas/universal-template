<!-- capsule-v2 -->
# AwaitVerify Managed Client — signed-URL uploads with an omit-means-no-document contract

**Source:** awaithumans Apache-2.0 `main@bc05b8e7`; Codebase Memory `mnt-hdd-utopia-inspo-awaithumans`. **Question:** How does the SDK talk to the managed backend so DEKs stay client-side and "no document" is unambiguous?

## Three control-plane calls + one raw PUT; explicit-null vs omitted distinction
**Path/Symbol:** `packages/python/awaithumans/awaitverify/_managed_client.py` — frozen dataclasses `FragmentSlot/UploadSession/CreatedTask/PolledTask` (:32-61), `ManagedBackendError` (:64-79), `create_upload_session` (:82-114), `upload_fragment` (:117-137), `create_task` (:140-188), `poll_task` (:191-213), `_post_json` (:216-228). Errors taxonomy in `awaitverify/errors.py` (what→why→fix→docs pattern; `VerifyDepsMissingError` :60-78).
**Signature:** `poll_task(*, managed_url, api_key, task_id, timeout_seconds: int = 25)` — long-poll GET with client timeout `timeout_seconds + 10.0`; upload PUT timeout sized from `AWAITVERIFY_UPLOAD_TIMEOUT_SECONDS` for slow residential uplinks under concurrency.
**Data Shape:** UploadSession carries plaintext `dek: bytes` ("kept in caller memory only") + per-fragment `{page_index, fragment_index, key, upload_url, upload_headers, expires_at_unix}`.

### Decisive source
```python
# Only include upload_session_id / task_metadata / initial_response when set so
# the managed backend's schema validation doesn't see an ambiguous explicit null
# where "omitted" is the correct signal. Omitting upload_session_id selects the
# no-document path.
if upload_session_id is not None:
    body["upload_session_id"] = upload_session_id
```
ManagedBackendError.hint maps status classes for the caller: 401/403 → check api_key, 404 → unknown id, 422 → field validation (read body), 5xx → transient/retry.

**Flow:** uploads endpoint mints fragment slots + DEK → SDK encrypts fragments CLIENT-side (five-fragment-masking capsule) → PUT each ciphertext to its signed URL (200/201 else ManagedBackendError) → create_task with upload_session_id (+ optional initial_response carrying Flow-A prior extraction or Flow-B output, JSON-safe via mode="json" discipline) → long-poll until terminal → response_json.
**Invariant:** the document NEVER leaves the customer environment unencrypted; omitted-vs-null is load-bearing wire semantics, not style.
**Probe:** `packages/python/tests/awaitverify/test_client.py::TestInitialResponseForwarding` (`test_flow_a_prior_extraction_forwarded_as_initial_response`:403 pins model_dump(mode="json") forwarding; stubbed _managed calls capture all three branches).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-awaithumans", query: "create_upload_session upload_fragment poll_task ManagedBackendError FragmentSlot", limit: 5 });
```
Live rank-1..3+5 line-exact (:117-137, :82-114, :191-213, error class :67-79).

## Verdict
Adopt the three-call surface, client-side DEK handling, and omit-vs-null rule; adapt endpoint paths/status mapping to your backend; keep the typed-error hint ladder — it's what makes 422s debuggable without support tickets.

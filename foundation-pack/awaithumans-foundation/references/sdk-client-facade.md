<!-- capsule-v2 -->
# AwaitHumans client facade — how do you bind multi-primitive config once, keep heavy imports lazy, and offer sync bridges without duplicating logic?

**Source:** awaithumans Apache-2.0 `main@bc05b8e7`; Codebase Memory `mnt-hdd-utopia-inspo-awaithumans`. **Question:** How should an SDK expose one configured client object over several primitives (human tasks, document verification, review) plus module-level shims without import-time weight or logic duplication?

## Configured facade over lazily-imported implementations
**Path/Symbol:** `packages/python/awaithumans/instance.py:AwaitHumans` (:46–235) + `get_default_client`/`set_default_client` (:243–260).
**Signature:** `AwaitHumans(*, api_key=None, server_url=None, managed_url=None, openai=None, anthropic=None, azure_openai=None, reducto=None, azure_di=None)`; methods `await_human / verify_document / await_review` each with `_sync` twin and camelCase alias (`awaitHuman`, `awaitVerifySync`, …).
**Data Shape:** constructor resolves `api_key`←arg→`AWAITHUMANS_API_KEY`, `server_url`←arg→`AWAITHUMANS_SERVER_URL`, `managed_url`←arg→env→hard default `https://api.awaithumans.dev`. Provider creds ride as typed objects (`OpenAI(api_key=…)`), never bare strings.

### Decisive source
```python
async def await_human(self, *, task, payload_schema, payload, response_schema,
                      timeout_seconds, assign_to=None, notify=None, verifier=None,
                      idempotency_key=None, redact_payload=False) -> T:
    from awaithumans.client import await_human as _await_human  # noqa: PLC0415
    return await _await_human(..., server_url=self.server_url, api_key=self.api_key)

def await_human_sync(self, **kwargs: Any) -> Any:
    return asyncio.run(self.await_human(**kwargs))

def get_default_client() -> AwaitHumans:      # module-level shims lazily share this
    global _default_client
    if _default_client is None:
        _default_client = AwaitHumans()
    return _default_client
```

**Flow:** construct once (explicit args win → env fallbacks → hosted default) → each call imports its implementation INSIDE the method body → forwards the bound `server_url`/`api_key` (or `self` as the credential carrier for managed calls) → sync variants wrap `asyncio.run`; camelCase aliases are one-line forwards, and module-level functions delegate to `get_default_client()`.
**Invariant:** heavy transport/provider imports stay function-local (module top level stays import-cheap for Temporal-workflow sandbox replay — same law as the deferred httpx import pinned in `references/await-human-poll-loop.md`); the facade owns ZERO business logic, it only binds configuration and forwards, so primitive semantics live in exactly one place.
**Probe:** `packages/python/tests/awaitverify/test_client.py` :183–218 `TestAwaitHumansClient` — api_key binding, managed_url default vs explicit vs `AWAITHUMANS_MANAGED_URL` env override, typed provider kwargs for four providers.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-awaithumans", query: "AwaitHumans get_default_client facade lazy import", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-layer shape: configured facade → lazy function-local imports → thin aliases/sync bridges, plus a settable process-wide default client for tests and framework DI. Adapt the env-var names, provider roster, and the managed-hosted default URL to your product. Omit the managed-product billing/priority vocabulary (`priority=`, per-page billing) — that belongs to the SaaS twin, not the facade pattern.

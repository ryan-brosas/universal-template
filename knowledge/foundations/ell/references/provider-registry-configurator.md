<!-- capsule-v2 -->
# provider registry and configurator — how do clients map to providers and models to clients at call time?

**Source:** ell MIT `main@9d129846203e75efeb4e5cddd3fb1c164dc0b243`; Codebase Memory `ext-ell`. **Question:** How do I resolve, per call, which provider executes a client and which client serves a model — including test-time overrides and unknown-model fallback?

## two registries + thread-local override stack
**Path/Symbol:** `src/ell/configurator.py:Config` (:35-185; `register_model` :93-108, `model_registry_override` :110-130, `get_client_for` :132-157, `register_provider` :159-169, `get_provider_for` :171-185), singleton `config = Config()` (:190).
**Signature:** `get_client_for(model_name: str) -> Tuple[Optional[client], bool]`; `get_provider_for(client) -> Optional[Provider]`.
**Data Shape:** `registry: Dict[str, _Model]` (frozen dataclass: name, default_client, supports_streaming); `providers: Dict[Type, Provider]`; override stack on `threading.local`.

### Decisive source
```python
# configurator.py:171-185
def get_provider_for(self, client):
    client_type = type(client) if not isinstance(client, type) else client
    for provider_type, provider in self.providers.items():
        if issubclass(client_type, provider_type) or client_type == provider_type:
            return provider
    return None
```

```python
# configurator.py:141-154 — fallback flag semantics
current_registry = self._local.stack[-1] if hasattr(
    self._local, 'stack') and self._local.stack else self.registry
model_config = current_registry.get(model_name)
fallback = False
if not model_config:
    warning_message = f"Warning: A default provider for model '{model_name}' could not be found. Falling back to default OpenAI client from environment variables."
    ...
    client = self.default_client
    fallback = True
```

**Flow:** providers register by *type* (`register_provider(openai_provider, openai.Client)` in each provider module; anthropic registers three client types incl. Bedrock/Vertex). Resolution at LMP call time (`complex.py:_client_for_model`): explicit client arg → registry lookup (with override-stack top first) → default client with `fallback=True`. The subtle branch: `not client and not was_fallback` raises the loud no-API-key error, but a fallback miss stays silent until the provider assert — an unregistered model with a configured default client is legal by design. `model_registry_override` copies-and-pushes the dict under the lock so concurrent threads see consistent snapshots.
**Invariant:** provider lookup is type-based subclass matching (a Client subclass routes to its parent's provider); model lookup is exact-name. The two-tier "silent fallback vs loud error" split must survive any port or every typo'd model name becomes a crash.
**Probe:** `tests/test_openai_provider.py:test_translate_to_provider_unregistered_model` (:100-120) pins unregistered-name behavior end-to-end through translation.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ell", query: "get client for model fallback", limit: 5, fields: ["signature", "name", "file"] });
// rank-1: ext-ell.src.ell.lmp.complex._client_for_model @ src/ell/lmp/complex.py:112-127
```

## Verdict
Adopt dual registries (provider-by-type, model-by-name) plus the thread-local override stack for tests. Adapt the OpenAI-default fallback to your house provider. Omit the deprecated `set_store` shim and the version-check phone-home that shares this module's init path.

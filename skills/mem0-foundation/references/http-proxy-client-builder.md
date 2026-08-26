<!-- capsule-v2 -->
# Config-level HTTP proxy builder — how do per-scheme proxy dicts become an httpx client without touching request code?

**Source:** mem0 MIT `main@8d5b7865`; Codebase Memory `mnt-hdd-utopia-inspo-memory-mem0`. **Question:** where does proxy support attach so every LLM/embedder config can route through a proxy with zero per-provider plumbing?

## Connected graph-selected seam
**Path/Symbol:** `mem0/utils/http.py`: `build_http_client` (:6-13); consumed by BOTH config bases at construction — `mem0/configs/llms/base.py:78` and the embeddings base equivalent.
**Signature:** `build_http_client(http_client_proxies: Optional[Union[Dict, str]]) -> Optional[httpx.Client]`.
**Data Shape:** None/falsy ⇒ None (no client); dict = `{scheme_prefix: proxy_url}` mounts; str = single proxy for all schemes. The built client lands on the config as `.http_client` and is passed into provider SDK constructors (e.g. AzureOpenAI `http_client=self.config.http_client`).

### Decisive source
```python
if not http_client_proxies:
    return None
if isinstance(http_client_proxies, dict):
    return httpx.Client(
        mounts={scheme: httpx.HTTPTransport(proxy=url) for scheme, url in http_client_proxies.items()}
    )
return httpx.Client(proxy=http_client_proxies)
```

**Flow:** pydantic config field `http_client_proxies` → base __init__ builds the client EAGERLY at config construction → providers that accept an httpx client receive it; everything downstream (OpenAI/Azure SDKs) honors its own transport, so no provider file knows proxies exist.
**Invariant:** falsy input must return None (not a default client) — tests pin `config.http_client is None` when unset; dict vs str select mount-table vs whole-client proxy modes, and both produce a real `httpx.Client` instance (asserted by isinstance). Building at CONFIG time (not call time) means one client per config object and lets factory-created providers inherit it unchanged.
**Probe:** `grep -rn "build_http_client" mem0/configs/llms/base.py mem0/configs/embeddings/base.py mem0/utils/http.py` (definition + exactly two consumption sites).
**Direct test:** `tests/test_http_client_proxies.py` — string/dict/absent parametrized over BOTH BaseLlmConfig and BaseEmbedderConfig (:10-29) + factory-preservation through LlmFactory.create (:31-39).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-memory-mem0", query: "build_http_client http_client_proxies httpx", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt config-construction-time proxy client building via httpx mounts for any multi-provider SDK fleet; adapt scheme keys to your transport library's mount grammar; omitting the None case or deferring construction breaks the pinned contract. Fully direct-tested (no caveat).

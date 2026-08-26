<!-- capsule-v2 -->
# Embedding provider match table — which arms have hidden constructor requirements a porter will trip on?

**Source:** gpt-researcher Apache-2.0 `main@5d84d2f5553e70a2765a8ff3a0d2672d60437ce8`; Codebase Memory `gpt-researcher`. **Question:** How does Memory instantiate 20 embedding providers, and which arms carry non-obvious env/parameter contracts?

## Memory.__init__ match statement
**Path/Symbol:** `gpt_researcher/memory/embeddings.py:74-227` (`Memory`), `:32-54` (`_SUPPORTED_PROVIDERS` set incl. netmind/openrouter/minimax/nebius).
**Signature:** `def __init__(self, embedding_provider: str, model: str, **embedding_kwargs: Any)` — raises `Exception("Embedding not found.")` for unknown providers; lazy per-arm imports keep unused provider deps optional.
**Data Shape:** Produces any LangChain Embeddings instance; consumed by ContextCompressor/WrittenContentCompressor via `researcher.memory.get_embeddings()`.

### Decisive source
```python
case "custom":
    _embeddings = OpenAIEmbeddings(
        model=model,
        openai_api_key=os.getenv("OPENAI_API_KEY", "custom"),
        openai_api_base=os.getenv("OPENAI_BASE_URL", "http://localhost:1234/v1"),
        check_embedding_ctx_length=False,   # quick fix for lmstudio
        **embedding_kwargs)
case "ollama":
    from langchain_ollama import OllamaEmbeddings
    _embeddings = OllamaEmbeddings(model=model,
                                   base_url=os.environ["OLLAMA_BASE_URL"],  # REQUIRED — KeyError if unset
                                   **embedding_kwargs)
```

**Flow:** config parses `EMBEDDING = "provider:model"` → match arm builds client (openai arm honors OPENAI_BASE_URL only when caller didn't pass one) → embeddings shared for similarity filtering AND written-content dedupe.
**Invariant:** `custom`/lmstudio MUST disable context-length checking (tokenization of arbitrary local models otherwise errors); ollama intentionally uses bare `os.environ[...]` so a missing URL crashes at construction, not mid-research. Deprecated `EMBEDDING_PROVIDER` env path rewrites the MODEL per provider and raises for unknowns (`config.py:98-126`).
**Probe:** battery P17a-b GREEN (`check_embedding_ctx_length=False` ×1; `raise Exception("Embedding not found.")` ×1).

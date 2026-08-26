<!-- capsule-v2 -->
# VertexAI embedder auth-fallback sandwich — rich authenticator first, legacy env-var behavior on any failure

**Source:** mem0 MIT `main@8d5b7865`; Codebase Memory `mnt-hdd-utopia-inspo-memory-mem0`. **Question:** how does the embedder keep the old `GOOGLE_APPLICATION_CREDENTIALS`-only contract alive after gaining the multi-method GCP authenticator?

## Connected graph-selected seam
**Path/Symbol:** `mem0/embeddings/vertexai.py`: `VertexAIEmbedding.__init__` (:12-42).
**Signature:** `__init__(self, config: Optional[BaseEmbedderConfig] = None)`.
**Data Shape:** config carries `vertex_credentials_json` plus getattr-probed optional fields (`google_service_account_json`, `google_project_id`) that BaseEmbedderConfig may not define.

### Decisive source
```python
try:
    GCPAuthenticator.setup_vertex_ai(
        service_account_json=getattr(self.config, 'google_service_account_json', None),
        credentials_path=self.config.vertex_credentials_json,
        project_id=getattr(self.config, 'google_project_id', None)
    )
except Exception:
    # Fall back to original behavior for backward compatibility
    credentials_path = self.config.vertex_credentials_json
    if credentials_path:
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
    elif not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        raise ValueError("Google application credentials JSON is not provided. ...")
```

**Flow:** try the full authenticator ladder → ANY exception (missing dep, bad file, no ADC) ⇒ bare-except fallback that mimics the pre-refactor contract: set the env var from `vertex_credentials_json`, or demand it's already set, else ValueError. Note the asymmetry: the fallback SETS the env var when a path exists but only VALIDATES it otherwise — it never re-checks the path.
**Invariant:** backward compatibility beats error fidelity here: an exception from rung 1 is swallowed wholesale (`except Exception:`), so misconfigurations surface as the legacy "credentials JSON is not provided" message rather than the authenticator's richer diagnosis. Porters must NOT "fix" this into specific exception handling without preserving the env-var mutation side effect downstream SDKs depend on. The task-type map is the second half of the seam: `add`/`update` default `RETRIEVAL_DOCUMENT`, `search` defaults `RETRIEVAL_QUERY`, and unknown action ⇒ ValueError before any API call.
**Probe:** `grep -cF 'except Exception:' mem0/embeddings/vertexai.py` (=1); `grep -cF 'elif not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):' mem0/embeddings/vertexai.py` (=1); `grep -cF 'embedding_type = "SEMANTIC_SIMILARITY"' mem0/embeddings/vertexai.py` (=2).
**Probe (direct test):** `tests/embeddings/test_vertexai_embeddings.py::test_embed_with_memory_action` (:92, loops all eight task types × add/update/search asserting `TextEmbeddingInput(text=..., task_type=...)`) plus `::test_credentials_from_environment` (:118) and `::test_missing_credentials` (:127) pinning the fallback arm's env-var contract.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-memory-mem0", query: "VertexAIEmbedding setup_vertex_ai GOOGLE_APPLICATION_CREDENTIALS fallback", limit: 10 });
```

## Verdict
Adopt the sandwich (rich ladder → bare-except legacy emulation) whenever extending an authenticated client without breaking old configs; adapt the config field names; omit specific-exception refactors that change which error message legacy users see.

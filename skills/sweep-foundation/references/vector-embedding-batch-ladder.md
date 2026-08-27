<!-- capsule-v2 -->
# Vector embedding batch ladder — how do you embed thousands of code snippets across three providers with cache-first batching, split-in-half recovery, and provider-namespaced caches?

**Source:** sweep (Apache-2.0) `main@a8b8b67bda4f`; Codebase Memory `sweep`. **Question:** What is the full ladder from a list of snippet texts to a [queries × docs] cosine-similarity matrix, including every failure-recovery rung and the cache-namespace rule that keeps providers from contaminating each other?

## openai_with_expo_backoff → openai_call_embedding → router: cache-first, split-in-half, truncate-and-retry
**Path/Symbol:** `sweepai/core/vector_db.py:openai_with_expo_backoff` (:198–253), `openai_call_embedding` (:176–194), `openai_call_embedding_router` (:129–173), `embed_text_array` (:105–127), `multi_get_query_texts_similarity` (:50–63), `normalize_l2` (:65–74), `chunk` (:39–47).
**Signature:** `multi_get_query_texts_similarity(queries: list[str], documents: list[str]) -> list[list[float]]` (one score-list per query); `openai_call_embedding(batch: list[str], input_type: str = "document") -> np.ndarray`.
**Data Shape:** per-text diskcache key `hash_sha256(text) + CACHE_VERSION`; `CACHE_VERSION = "v2.1.1" + ("-voyage-aws" | "-voyage" | "")` — the suffix switches with the active provider; all embeddings L2-normalized; OpenAI branch cuts `text-embedding-3-small` to 512 dims (`[:, :512]`).

### Decisive source
```python
# provider router — AWS SageMaker → Voyage → OpenAI, all L2-normalized
if VOYAGE_API_USE_AWS:
    ... sm_runtime.invoke_endpoint(EndpointName=VOYAGE_API_AWS_ENDPOINT_NAME, ...)
elif VOYAGE_API_KEY:
    result = client.embed(batch, model="voyage-code-2", input_type=input_type, truncation=True)
    normalized_dim = normalize_l2(cut_dim)
else:
    response = client.embeddings.create(input=batch, model="text-embedding-3-small", encoding_format="float")
    cut_dim = np.array([data.embedding for data in response.data])[:, :512]
    normalized_dim = normalize_l2(cut_dim)

# recovery ladders — error-string-matched, not exception-type-matched
except (voyageai_error.InvalidRequestError, ClientError) as e:
    if len(batch) > 1 and "Please lower the number of tokens in the batch." in str(e):
        mid = len(batch) // 2
        left = openai_call_embedding(batch[:mid], input_type)
        right = openai_call_embedding(batch[mid:], input_type)
        return np.concatenate((left, right))
    else:
        raise e
except openai.BadRequestError as e:
    if "maximum context length" in str(e):
        batch = [tiktoken_client.truncate_string(text) for text in batch]
        return openai_call_embedding(batch, input_type)

# backoff covers ONLY Timeout; generic errors get the >8192-token truncate-or-raise ladder
@backoff.on_exception(backoff.expo, requests.exceptions.Timeout, max_tries=5)
def openai_with_expo_backoff(batch: tuple[str]):
    ...
    assert len(indices) == len(new_embeddings)   # splice integrity after partial cache hits
```

**Flow:** embed_text_array (""→" " hygiene, BATCH_SIZE slicing; the Pool branch is dead — `workers = min(max(1, cpu_count() // 4), 1)` is always 1) → per batch: cache lookup for every text, send only misses → router picks provider by env (AWS triple key → Voyage key → OpenAI) → on token-overflow: Voyage/SageMaker "Please lower the number of tokens in the batch." ⇒ recursive split-in-half and concat; OpenAI "maximum context length" ⇒ tiktoken-truncate all texts to 8192 and retry whole batch; generic Exception ⇒ truncate-and-retry only if ANY text > 8192 tokens else re-raise; Timeout ⇒ expo backoff max_tries=5 → splice new embeddings into the cached positions (assert count equality) → write ALL entries back to cache → multi_get_query_texts_similarity embeds documents once (input_type="document") and queries separately (input_type="query" — asymmetric retrieval) → `1 - cdist(a, B, metric='cosine')` (scipy) → [num_queries × num_docs].
**Invariant:** The provider suffix in CACHE_VERSION is load-bearing: document embeddings from voyage-code-2 and text-embedding-3-small live in different vector spaces, so a port that shares one cache namespace across providers silently scores cross-provider pairs. The split-in-half recursion must check `len(batch) > 1` or a single over-long text recurses forever. The `assert len(indices) == len(new_embeddings)` guards the splice after partial cache hits — drop it and one cache miss shifts every later embedding by one slot. Error-string matching couples the ladder to provider wording; a port should prefer structured error codes where the provider offers them, but keep the string match as fallback.
**Probe:** No offline-runnable test exists (no direct test file for vector_db at pin; import chain needs scipy/numpy/voyageai/boto3 — scipy/numpy/voyageai absent from system python). Deterministic probes at pin: `grep -n 'CACHE_VERSION = ' sweepai/core/vector_db.py` → :27 (commented-out v2.0.04 line) and :29 ("v2.1.1" + suffix); `grep -n 'workers = min'` → :109; `grep -n 'max_tries=5'` → :200; `grep -n 'batch\[:mid\]'` → :184; `grep -n '\[:, :512\]'` → :171; `grep -n 'input_type="query"'` → :56; `grep -rn 'chunk(' --include='*.py' sweepai/` → zero callers of vector_db.chunk (dead, definition only at :39); `grep -rn 'batch_by_token_count_for_voyage' --include='*.py' .` → definition only (:76, dead).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "sweep", query: "openai_call_embedding_router embed_text_array backoff voyage sagemaker", limit: 10 });
// NOT executed this session (Codebase Memory MCP not connected); direct source read of
// vector_db.py (255L whole) at pin substituted — see verification.md pass 4.
```

## Verdict
Adopt the cache-first batch (per-text hash+version keys, send-only-misses, splice-with-assert), the two distinct token-overflow recoveries (split-in-half for batch-token caps vs truncate-to-context for per-text caps), the Timeout-only backoff placement, the asymmetric query/document input_type, and the provider-suffixed cache version. Adapt the provider ladder to your available embedding services and replace error-string matching with typed errors where possible. Omit the dead Pool branch, the dead chunk()/batch_by_token_count_for_voyage helpers, and the boto3 client created per call (hoist it). Coverage caveat: no live direct test at pin.

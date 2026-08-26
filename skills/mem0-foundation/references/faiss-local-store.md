<!-- capsule-v2 -->
# FAISS local store — how do you persist a vector index plus docstore safely (restricted pickle, JSON migration, cosine-via-IP) and delete by full rebuild?

**Source:** mem0 MIT `main@8d5b7865`; Codebase Memory `mnt-hdd-utopia-inspo-memory-mem0`. **Question:** what does a porter need to keep so an embedded FAISS store survives restarts, resists malicious pickle files, and keeps cosine/euclidean scores and ID maps consistent?

## Connected graph-selected seam
**Path/Symbol:** `mem0/vector_stores/faiss.py`: `SafeUnpickler` whitelist (:34-60) + `_safe_pickle_load` (:63-77) + `_validate_docstore_structure` (:80-118); load ladder `_load` (:174-226, JSON-over-pickle + auto-migrate :212-214), `_save` (:227-249), `_should_normalize` (:251-262), score squash in `_parse_output` (:264-307), insert ID assignment (:368-371, `starting_idx = len(self.index_to_id)`), post-filter fetch_k×2 search (:403-415), delete-by-reconstruct-rebuild (:461-482). Direct tests `tests/vector_stores/test_faiss.py`: `test_normalize_L2` (:333-349), `TestSafePickleLoad::test_safe_pickle_load_blocks_malicious_file` (:466-485).
**Signature:** `FAISS(collection_name, path=None, distance_strategy="euclidean", normalize_L2=False, embedding_model_dims=1536)`; `_parse_output(scores, ids, top_k) -> List[OutputData]`.
**Data Shape:** on disk `<path>/<collection>.faiss` + `.json` docstore `{docstore: {id→payload}, index_to_id: {str(idx)→id}}`; legacy `.pkl` accepted read-only then auto-migrated; in memory `index_to_id` keys are positional int row numbers.

### Decisive source
```python
class SafeUnpickler(pickle.Unpickler):
    SAFE_MODULES = frozenset({"builtins", "__builtin__"})
    SAFE_NAMES = frozenset({"dict","list","str","int","float","bool","tuple","set","frozenset","NoneType"})
    def find_class(self, module, name):
        if module in self.SAFE_MODULES and name in self.SAFE_NAMES:
            return getattr(builtins, name)
        raise pickle.UnpicklingError(f"Unsafe pickle: attempted to load '{module}.{name}'. ...")

def _should_normalize(self) -> bool:
    # cosine is implemented on IndexFlatIP which equals cosine ONLY for unit vectors
    if strategy == "cosine": return True          # ALWAYS normalize for cosine
    return self.normalize_L2 and strategy == "euclidean"   # euclidean: opt-in flag

raw_score = float(scores[i])
if self.distance_strategy.lower() == "euclidean":
    score = 1.0 / (1.0 + raw_score)               # distance → pseudo-similarity squash
else:
    score = raw_score                              # IP/cosine already similarity-shaped
```
```python
# delete = reconstruct survivors, reset, re-add, RENUMBER the id map (positions shift!)
remaining_vectors, new_index_to_id, new_idx = [], {}, 0
for old_idx in sorted(self.index_to_id.keys()):
    if old_idx == index_to_delete: continue
    remaining_vectors.append(self.index.reconstruct(int(old_idx)))
    new_index_to_id[new_idx] = self.index_to_id[old_idx]; new_idx += 1
self.index.reset(); self.index.add(np.array(remaining_vectors, dtype=np.float32))
self.docstore.pop(vector_id, None); self.index_to_id = new_index_to_id
```

**Flow:** ctor makes dirs → if index+docstore exist, `_load` prefers JSON (string keys converted back to int), falls back to restricted-pickle with structure validation and immediately `_save()`s JSON (one-way migration); else `create_col` builds IndexFlatIP (inner_product/cosine) or IndexFlatL2 → insert normalizes per `_should_normalize`, assigns IDs positionally from `len(index_to_id)` → search multiplies fetch_k by 2 when filters present, filters POST-hoc over payload dicts until top_k filled → every mutation ends in `_save()`. Load failures degrade to EMPTY stores after a warning (:222-225).
**Invariant:** (1) unpickling is whitelisted to builtins-only — arbitrary-code-execution via crafted pickle is the threat model, and malformed files become ValueError not crash; (2) cosine REQUIRES normalization (IP≠cosine otherwise) while euclidean leaves it user-opt-in; (3) deletion renumbers ALL row positions — any port that deletes by swapping/removing single rows corrupts index_to_id permanently; (4) filtered search over-fetches ×2 BEFORE filtering because post-filtering consumes candidates; (5) `-1` sentinel ids and unknown ids are skipped silently in parse; (6) JSON is the security boundary going forward — pickle path exists only as read-once migration.
**Probe:** `tests/vector_stores/test_faiss.py::TestSafePickleLoad::test_safe_pickle_load_with_valid_file` / `::test_safe_pickle_load_blocks_malicious_file`, `::test_normalize_L2`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-memory-mem0", query: "SafeUnpickler _safe_pickle_load _should_normalize", limit: 10, fields: ["signature", "name", "file"] });
```
(resolved live pre-write: faiss.py 63-77/47-60 + tests/vector_stores/test_faiss.py 333-349/453-485)

## Verdict
Adopt the restricted-unpickler whitelist, JSON-preferred migration, always-normalize-cosine rule, and rebuild-on-delete verbatim; adapt file layout/distance set to your storage conventions; omit legacy-pickle support entirely in greenfield ports (JSON only) — the safe-unpickler exists solely to digest old unsafe stores.

<!-- capsule-v2 -->
# EmbeddingBase embed_batch default — sequential fallback contract with opt-in native override

**Source:** mem0 MIT `main@8d5b7865`; Codebase Memory `mnt-hdd-utopia-inspo-memory-mem0`. **Question:** what must EVERY mem0 embedder subclass provide, and which batch behavior is inherited vs overridden?

## Connected graph-selected seam
**Path/Symbol:** `mem0/embeddings/base.py`: `EmbeddingBase.__init__` (:14-18) + `embed_batch` (:33-50); abstract `embed` (:21-31).
**Signature:** `embed(self, text, memory_action: Optional[Literal["add", "search", "update"]])` (abstract); `embed_batch(self, texts, memory_action="add") -> List[List[float]]`.
**Data Shape:** config defaults to a fresh `BaseEmbedderConfig()` when None; `embed_batch` returns one vector per input text, order-preserving.

### Decisive source
```python
def embed_batch(self, texts, memory_action="add"):
    """Embed multiple texts. Override in subclasses for native batch support.

    Default implementation calls embed() sequentially for each text.
    Subclasses with native batch APIs (e.g., OpenAI) should override
    this for better performance.
    """
    return [self.embed(text, memory_action) for text in texts]
```

**Flow:** the ABC guarantees: (1) None-safe config materialization in `__init__`, so subclasses never guard against missing config; (2) `embed_batch` is ALWAYS available — sequential `embed()` calls by default — while native-batch backends (OpenAI's 100-shuffle re-sort, VertexAI's 250-chunk) replace it wholesale.
**Invariant:** the pipeline may call `embed_batch` on ANY registered embedder without capability probing — the base class is the compatibility shim. Two porting traps: overriding `embed_batch` but returning ragged/misordered results breaks every caller that zips texts↔vectors positionally (VertexAI even raises on count mismatch — see its capsule), and subclasses MUST accept the `memory_action` kwarg even if unused, or the sequential default's call signature diverges from the override's. The sibling `mem0/memory/base.py` `MemoryBase` ABC is the same pattern at the memory level: five abstract methods (get/get_all/update/delete/history) with NO concrete helpers — pure interface.
**Probe:** `grep -cF 'return [self.embed(text, memory_action) for text in texts]' mem0/embeddings/base.py` (=1); `grep -cF '@abstractmethod' mem0/memory/base.py` (=5).
**Coverage caveat:** the ABCs are exercised by every backend suite implicitly (mock fixtures subclass them); no dedicated unit test pins the sequential default itself.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-memory-mem0", query: "EmbeddingBase embed_batch override sequential", limit: 10 });
```

## Verdict
Adopt the None-config-materializing ABC + always-available sequential batch shim when defining pluggable embedder interfaces; adapt method sets to your surface; omit capability-probing call sites — the base-class default is the probe.

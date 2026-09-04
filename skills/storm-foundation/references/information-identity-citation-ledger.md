<!-- capsule-v2 -->
# Information identity & citation-uuid ledger — what makes two retrieved facts "the same source" and when does a fact earn a permanent citation number?

**Source:** storm MIT `main@fb951af7`; Codebase Memory `storm`. **Question:** How do you deduplicate retrieval results into stable citation ids without a database, and why must identity exclude the description field?

## Connected graph-selected seam
**Path/Symbol:** `knowledge_storm/interface.py:Information` (:41-133) + `knowledge_storm/dataclass.py:KnowledgeBase.insert_information` (:680-713).
**Signature:** `__hash__ = int(md5(json((url, tuple(sorted(snippets)), _meta_str())), 16))`; `insert_information(path: str, information: Information, missing_node_handling="abort", root=None)`.
**Data Shape:** Identity = (url, sorted snippet set, meta question/query string). `description`, `title`, and `citation_uuid` are deliberately NOT part of identity. Ledger maps: `info_hash_to_uuid_dict: Dict[int,int]`, `info_uuid_to_info_dict: Dict[int, Information]`.

### Decisive source
```python
def __hash__(self):   # second definition wins; the tuple-hash version at :70-76 is dead code
    return int(self._md5_hash((self.url, tuple(sorted(self.snippets)), self._meta_str())), 16)

# inside KnowledgeBase.insert_information — under self._lock:
information_hash = hash(information)
if information.citation_uuid == -1:
    info_citation_uuid = self.info_hash_to_uuid_dict.get(
        information_hash, len(self.info_hash_to_uuid_dict) + 1)   # claim-or-mint, 1-based
    information.citation_uuid = info_citation_uuid               # MUTATES the shared object
    self.info_hash_to_uuid_dict[information_hash] = info_citation_uuid
    self.info_uuid_to_info_dict[info_citation_uuid] = information
```

**Flow:** Fresh retrievals arrive with `citation_uuid=-1` → hash computed → existing hash reuses its uuid (dedup); new hash mints `len+1` (1-based, gap-free while no deletions) → uuid stamped onto the object itself so every later consumer sees the same number → node content stores uuid ints; `meta["placement"]` records the `" -> "` path.
**Invariant:** (1) `citation_uuid == -1` is the "unclaimed" sentinel — minting happens exactly once under the KB lock. (2) Because uuid lives on the object, aliasing the same Information instance shares the citation; deep-copying SPLITS identity. (3) Hash includes meta question/query: same URL retrieved for different queries is NOT deduped. (4) The class defines `__hash__` twice; the md5 version (:87-91) silently overrides the plain-tuple one — porters copying only :70-91 partially get different ids.
**Probe:** executed lifted probe GREEN this pass (`Information.__hash__` resolves via graph to interface.py:87-91; pins in `.pi/work/foundations-deep-farm/scratch-storm-pass1/probe_gate5.py`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "storm", query: "insert_information citation_uuid hash dedup lock", limit: 10 });
```

## Verdict
Adopt content-addressed citation minting (hash→uuid ledger, mutate-once) for any grounded-writing system; adapt the identity tuple to your schema; omit the dead first `__hash__`. Related: `ConversationTurn` serializes `cited_info: None` on purpose (:65) — cited info is rebuilt from the KB ledger, never round-tripped. Caveat: no upstream tests; source-pinned.

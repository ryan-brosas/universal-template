<!-- capsule-v2 -->
# Knowledge-base mind-map lifecycle — how does Co-STORM's tree stay clean while information pours in?

**Source:** storm MIT `main@fb951af7`; Codebase Memory `storm`. **Question:** What is the exact reorganize() ordering and the node-merging rules that keep a hierarchical knowledge base coherent?

## Connected graph-selected seam
**Path/Symbol:** `knowledge_storm/dataclass.py:KnowledgeBase.reorganize` (:828-846) + `trim_empty_leaf_nodes` (:715-732) + `merge_single_child_nodes` (:752-771) + `insert_from_outline_string` (:514-538).
**Signature:** `reorganize()`; `trim_empty_leaf_nodes()`; `merge_single_child_nodes()`; `insert_information(path, information, missing_node_handling="abort")`.
**Data Shape:** `KnowledgeNode.content: Set[int]` (citation uuids); tree of named nodes; info registry maps uuid→Information with `meta["placement"]` path strings.

### Decisive source
```python
def reorganize(self):
    self.trim_empty_leaf_nodes();  self.merge_single_child_nodes()   # pre-clean
    self.expand_node_module(knowledge_base=self)                     # LLM subtopic expansion
    self.trim_empty_leaf_nodes();  self.merge_single_child_nodes()
    self.update_all_info_path()                                      # rewrite placements LAST
# merge rule: single child folds INTO parent (content union), grandchildren repointed:
if len(node.children) == 1:
    single_child = node.children[0]
    node.content.update(single_child.content)
    node.children = single_child.children
    for grandchild in node.children:
        grandchild.parent = node
# outline ingestion skips generic headers entirely:
if title.lower() in ["overview", "summary", "introduction"]: continue
```

**Flow:** Insertions place info uuids at path-resolved nodes (`missing_node_handling`: abort/create/raise-error) → when a node accumulates past `node_expansion_trigger_count`, LLM proposes subtopics → reorganize trims empty leaves bottom-up ITERATIVELY until leaf count stabilizes → single-child chains collapse upward → every surviving info's `meta["placement"]` is rewritten by a full traversal.
**Invariant:** (1) Order matters: trim+merge BEFORE expansion so the LLM sees a clean tree, and `update_all_info_path` strictly AFTER structural changes or placement metadata lies. (2) Merging unions content sets — citation numbers survive; DELETING a node without re-homing its content loses citations. (3) `find_node_by_path` splits on the literal `" -> "` separator used everywhere paths are rendered. (4) All insertions run under `self._lock`; hash→uuid minting shares that critical section.
**Probe:** deterministic pins GREEN — dataclass.py:817-822 latent no-op `.replace("[-1]", "")` byte-verified this pass; graph resolves `reorganize`/`trim_empty_leaf_nodes` line-exact.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "storm", query: "KnowledgeBase reorganize trim_empty_leaf merge_single_child", limit: 10 });
```

## Verdict
Adopt the clean→expand→clean→relabel pipeline for any LLM-maintained hierarchy; adapt trigger counts; note the turn-ingestion twin `update_from_conv_turn` renumbers utterance citations through `[_{new}_]` placeholders and carries the two latent no-op statements — port the INTENT, not those lines. Caveat: no upstream tests; source-pinned.

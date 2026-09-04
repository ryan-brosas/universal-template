<!-- capsule-v2 -->
# Repo map — whole-repo outline ranked by PageRank into a token budget

**Source:** Aider Apache-2.0 `main@5dc9490bb35f9729ef2c95d00a19ccd30c26339c`; Codebase Memory project `aider` (full index). **Question:** How can a harness show an LLM a whole repository inside a token budget, pointed at the identifiers the conversation just mentioned?

## Personalized PageRank map fitting
**Path/Symbol:** `aider/repomap.py`: `RepoMap.get_repo_map(chat_files, other_files, mentioned_idents, force_refresh)` (:103), `get_ranked_tags(...)` (:365), `get_ranked_tags_map` (:576), `render_tree` (:710), `to_tree` (:748).
**Signature:** `get_repo_map(...) -> str | None`; `get_ranked_tags(...) -> list[(fname,)|(fname, ident, tag)]`.
**Data Shape:** returns a Markdown outline string (or None when `no other_files`/`max_map_tokens<=0`); ranks are personalized PageRank over a file-to-file reference graph.

### Decisive source
```python
# mentioned identifiers and naming style multiply rank; snake/kebab/camel names win
if ident in mentioned_idents:
    mul *= 10
if (is_snake or is_kebab or is_camel) and len(ident) >= 8:
    mul *= 10
if ident.startswith("_"):
    mul *= 0.1
if len(defines[ident]) > 5:
    mul *= 0.1
# a chat file referencing an ident steeply boosts that definition's rank
if referencer in chat_rel_fnames:
    use_mul *= 50
# chat files steer rank but are never emitted
for (fname, ident), rank in ranked_definitions:
    if fname in chat_rel_fnames:
        continue
```

**Flow:** build `defines`/`references` from tree-sitter tags per file; add a low-weight self-edge for orphans; add weighted `referencer→definer` edges scaled by in-chat reference, naming style, and mentions; run `nx.pagerank` over a `MultiDiGraph` with a personalization vector; distribute rank and aggregate per definition; sort, skip chat files, then fit into `max_map_tokens`.
**Invariant:** chat files steer rank but are never emitted; mentioned/camel-snake-kebab identifiers rank higher; the map is always bounded by `max_map_tokens` and pathological repos disable the map rather than crash.
**Probe:** `tests/basic/test_repomap.py::test_get_repo_map_with_identifiers` (:163), `test_get_repo_map_excludes_added_files` (:246), `test_get_repo_map` (:21), `test_repo_map_refresh_*` (:49,:106).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "aider", query: "get_ranked_tags get_repo_map pagerank fit tokens", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the personalized-PageRank + token-budget fit as the reproducible context engine; keep chat-exclusion and rank multipliers as the behavioral contract. Adapt the tree-sitter tag stack to the host; omit Aider's specific language pack.

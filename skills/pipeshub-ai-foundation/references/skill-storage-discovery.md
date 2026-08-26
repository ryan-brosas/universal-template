<!-- capsule-v2 -->
# Skill storage & discovery — how do multi-root stores, a JSON index cache, and sync catalog snapshots stay consistent?

**Source:** pipeshub-ai (Apache-2.0) `main@4a02110dd9a7a644d8ba7a5ccd295c58a3c3628f`; Codebase Memory `pipeshub-ai`. **Question:** A porter implementing skill storage must know the read-only-vs-writable root model, the precedence rule on name collisions, why the prompt path needs a SYNC read model, and what every write must keep in sync.

## FilesystemSkillStore — one writable primary, read-only extras
**Path/Symbol:** `modules/providers/skills/filesystem_store.py:FilesystemSkillStore` (70-263); `_safe_join` escape guard (50-57); ABCs in `store.py` (SkillReader 22-39 / SkillWriter 42-80 / SkillStore 83 / SkillHistoryReader 88-113 / SkillCandidateStore 116-133).
**Signature:** ctor `(skills_dir, extra_skills_dirs=None, validator=None)`; `refresh()`; async CRUD per SkillStore.
**Data Shape:** In-memory `name -> skill_dir` location cache + `name -> (category, subcategory)` built at construction, updated by every write; `refresh()` rescans out-of-process changes. History/candidate queues are OPTIONAL store opt-ins via isinstance checks — manager degrades to filesystem fallbacks when absent.

### Decisive source
```python
# filesystem_store.py — precedence + writability + escape guard
for root in self._extra_roots:                 # extras FIRST (lower precedence)...
    for skill_dir, category, subcategory in iter_skill_dirs(root):
        locations[name] = skill_dir
for skill_dir, ... in iter_skill_dirs(self._primary):   # ...primary LAST (shadows)
    locations[name] = skill_dir

def _is_writable(self, skill_dir): return os.path.commonpath([skill_dir, self._primary]) == self._primary

def _safe_join(base, rel):
    full = os.path.abspath(os.path.join(base_abs, rel))
    if os.path.commonpath([full, base_abs]) != base_abs:
        return None                            # '../../etc/passwd' rejected
```

**Flow:** every mutation: resolve location → check writable (commonpath under primary) → validate → write → update caches. Read-only-root mutations fail closed (`SkillFormatError` on update; False on patch/delete/resource ops). Resource reads go through _safe_join (no traversal).
**Invariant:** Extra roots are for EXTERNALLY-owned skills (npx packs, team dirs, monorepo checkouts) — never written. Primary shadows extras on name collision (scan order is load-bearing). create_skill does NOT rewrite content to embed the placement category — it returns metadata with directory-defaults merged so callers can update catalogs without re-reading.
**Probe:** `tests/unit/agent_loop_lib/modules/providers/skills/test_filesystem_store.py` (TestConstructionAndRefresh pins precedence/shadowing; TestCreate/Update/Patch/Delete/Resources/Deprecate/ListSkillsFilter pin validation ordering, read-only refusal, resource round-trips incl. traversal).

## FilesystemSkillIndex — JSON cache + keyword scoring
**Path/Symbol:** `modules/providers/skills/filesystem_index.py:FilesystemSkillIndex` (39-123); haystack `text_scoring.py:skill_haystack` (15-21) over shared `core/text_scoring.py` tokenizer.
**Signature:** ctor `(primary_root, index_filename="index.json")`; `rebuild(skills)`; `search(query, filter=None, limit=10)`; add/remove/update_entry.
**Data Shape:** `_meta/index.json` in the PRIMARY root only (extra-root entries indexed there too but never written back to their own dirs). Entries are full SkillMetadata dicts. Corrupt cache ⇒ discard-with-warning, start empty.

### Decisive source
```python
# filesystem_index.py — DEPRECATED hides from search unless explicitly asked
if filter is None or filter.status is None:
    candidates = [m for m in candidates if m.status != SkillStatus.DEPRECATED]
...
if not query:
    return [SkillMatch(skill=m, relevance=1.0, match_reason="catalog") ...]
score, overlap = keyword_overlap_score(query_tokens, skill_haystack(m))
```

**Flow:** rebuild from store listing on start/refresh → search filters structurally (shared matches_filter), drops DEPRECATED by default (explicit status opt-in restores them), scores remaining against name+description+tags+concepts+category tokens, sorts desc, truncates. Every mutation saves the JSON cache immediately.
**Invariant:** The index is a CACHE, never truth — store remains source of fact; empty query means "list catalog" (relevance 1.0), not "match everything". DEPRECATED skills stay loadable by exact name while invisible to discovery (pairs with catalog_snapshot's exclusion). Semantic twin exists at the same ABC (`app/agents/agent_loop/skills/semantic_index.py`) swapping in via DI with zero other-module changes.

## Sync catalog snapshot (prompt-path constraint)
**Path/Symbol:** `manager.py:SkillManager.catalog_snapshot` (132-136) + refresh (120-128); docstring rationale (48-55).
**Signature:** `catalog_snapshot() -> list[SkillMetadata]` — deliberately SYNC.
**Data Shape:** In-memory `dict[name, SkillMetadata]` refreshed by start()/refresh(), kept current by EVERY mutation (create/update/delete/patch/deprecate/rollback all rewrite their entry).

### Decisive source
```python
# manager.py — DefaultPromptBuilder.build() is synchronous; no I/O allowed on the prompt path
def catalog_snapshot(self) -> list[SkillMetadata]:
    return [m for m in self._catalog.values() if m.status != SkillStatus.DEPRECATED]
```

**Flow:** start→refresh scans store + rebuilds index + rebuilds read model → prompt builder reads snapshot synchronously every turn → mutations update store, index entry, AND read model in the same call.
**Invariant:** One mutation must update all THREE surfaces (store, index, catalog) or they drift; tier-1 disclosure excludes DEPRECATED exactly like the index does. Async everywhere else, sync ONLY here — an await in the prompt builder is the bug this design prevents.
**Probe:** `tests/unit/agent_loop_lib/modules/providers/skills/test_manager.py::TestSearchAndCatalogQueries` + TestCrud/TestLifecycle (pins catalog/index co-update on writes and deprecate visibility rules).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pipeshub-ai", query: "FilesystemSkillStore refresh _is_writable", limit: 10 });
await mcp.codebase_memory.search_graph({ project: "pipeshub-ai", query: "FilesystemSkillIndex search rebuild", limit: 10 });
await mcp.codebase_memory.search_graph({ project: "pipeshub-ai", query: "catalog_snapshot", limit: 5 });
```

## Verdict
Adopt primary/extras multi-root storage with primary-shadows-extras precedence, commonpath writability checks, the _safe_join escape guard, corrupt-cache-discard resilience, deprecated-invisible-but-loadable semantics, and the three-surface write discipline with a sync read model for sync prompt builders. Adapt index backend (keyword vs embedding) behind the unchanged ABC; adapt limits/paths. Omit graph-backed store variants (`app/agents/adapter/test_skills_graph_store.py` territory) unless porting onto a graph DB host.

<!-- capsule-v2 -->
# Identity scoping — re-built, never trusted

**Source:** mem0 MIT `<branch>@<commit>`; Codebase Memory `mem0`. **Question:** how does a memory system keep each memory scoped to the identity (user/agent/run) that owns it, even when callers pass freeform metadata?

## Connected graph-selected seam
**Path/Symbol:** `mem0/memory/main.py`: `_build_filters_and_metadata` (:314-420), `_build_session_scope` (:412), `_escape_scope_value` (:407), `_strip_identity_keys` (:143).
**Signature:** `_build_filters_and_metadata(...)` returns TWO dicts — `base_metadata_template` (what gets STORED) and `effective_query_filters` (what gets QUERIED).
**Data Shape:** identity keys `user_id`/`agent_id`/`run_id`; scope values escaped via `_escape_scope_value`; session scope built via `_build_session_scope`.

### Decisive source
```ts
# base_metadata_template (stored): identity keys set ONLY from entity params,
#   same keys STRIPPED from caller-supplied metadata first (issue #6655)
#   — freeform metadata could otherwise place a memory into a scope the caller
#   never passed, and "re-pinning after the fact" cannot prevent it for unset params
# effective_query_filters (queried): adds the resolved actor —
#   precedence explicit actor_id arg -> filters["actor_id"]
```

**Flow:** identity keys are set only from entity params and stripped from caller metadata (so freeform metadata can't scope-jack a memory); the effective query filters add the resolved actor (explicit arg precedence over filters); scope values are escaped and the session scope is built deterministically.
**Invariant:** identity scope is re-built from entity params, never trusted from caller metadata; a memory can't be placed into a scope the caller never passed.
**Probe:** `tests/memory/` scoping tests (metadata with identity keys stripped; scope enforced on store + query; actor precedence).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mem0", query: "_build_filters_and_metadata scope identity user_id agent_id run_id", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the re-built identity scope (strip identity keys from caller metadata, set only from entity params); adapt the identity key set and scope vocabulary to host.

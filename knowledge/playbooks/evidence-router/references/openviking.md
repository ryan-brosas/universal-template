# OpenViking evidence and memory

OpenViking is an optional rebuildable cache over past experience: decisions,
failed attempts, recurring edge cases, and lessons that are expensive to
reconstruct. It is never the canonical owner of source facts, skills, or
session history, and it is never automatically synchronized or injected:
current project source, tests, and runtime behavior still decide what is
true.

## Retrieval

Use the narrowest operation that answers the question:

| Need | Operation |
|---|---|
| Exact symbol or error text | `memgrep` |
| Conceptual or semantic match | `memsearch` or `memfind` |
| Read a known `viking://` resource | `memread` |
| Enumerate resources | `memglob` or `membrowse` |

Treat every hit as a pointer. Read the cited source before relying on it. Probe
tool availability and corpus inventory at runtime; endpoints, paths, models,
and corpus counts are machine-local state and do not belong in repository
policy.

## Materialization

OpenViking material is a derived representation over canonical evidence, not a
hand-maintained conclusion database.

| Aspect | Contract |
|---|---|
| Canonical input | Current source at a Git revision, or project-scoped session JSONL |
| Derived representation | Indexed views and retrieval pointers over that input |
| Provenance | Source identity sufficient to reproduce or audit the material |
| Invalidation | Material is stale once the canonical input changes |
| Regeneration | Re-materialize from the canonical input; never hand-edit the cache |

Materialize on demand or under an explicitly approved workflow. Never
automatically synchronize every session into OpenViking, and never inject
materialized context into unrelated tasks or projects.

Session-derived provenance records `source_type: session-jsonl`, `project`,
`session_id`, `event_range`, `projector`, and `projector_version`.
Source-derived provenance records `source_type: git`, `repository`,
`revision`, `paths`, `projector`, and `projector_version`. Any equivalent
serialization that preserves auditability is acceptable.

Do not hand-maintain a cached conclusion: correct the canonical source or the
projector, erase the stale materialization, and regenerate it. Route reusable
code, gates, skills, references, or foundations through `leverage-capture`
instead of building a second prose archive.

If OpenViking is unavailable, fall back to the nearest reliable local source
and state the degraded evidence path.

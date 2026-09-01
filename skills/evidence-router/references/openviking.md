# OpenViking evidence and memory

OpenViking is the durable experience store for decisions, failed attempts,
recurring edge cases, and lessons that are expensive to reconstruct. It is a
retrieval aid, not implementation authority: current project source, tests,
and runtime behavior still decide what is true.

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

## Capture

Add material only when the experience itself is cheaper to retrieve than to
reconstruct. Do not duplicate an available repository, generated artifact, or
fact that a runtime probe can recover.

1. Add the source with the available OpenViking ingestion operation.
2. Wait for indexing to finish before semantic retrieval.
3. Retrieve against the narrow target resource and verify the source text.
4. Preserve provenance with the stored resource or memory entry.
5. Route reusable code, gates, skills, references, or foundations through
   `leverage-capture` instead of building a second prose archive.

If OpenViking is unavailable, use the nearest authoritative local source and
state the degraded evidence path.

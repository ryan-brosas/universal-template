# Codebase Memory rules for foundations

## The canonical loop

```text
index state -> bounded graph survey -> crown symbols -> trace -> coverage check
-> selective source/test confirmation -> reuse verdict -> concise skill
```

Use the same loop at authoring time and when the skill is later applied. The live graph keeps a foundation from becoming a frozen summary.

## Graph is the map; source is final

Use Codebase Memory instead of manual repository walking for:

- architecture and package orientation;
- symbol discovery and qualified names;
- inbound/outbound call paths and blast radius;
- hotspot and cluster evidence;
- coverage and freshness metadata.

Use direct source for:

- a clipped or partially parsed symbol;
- excluded or unindexed files;
- exact test behavior when tests are excluded;
- reconciling a graph edge with the implementation.

## Coverage decisions

| Status/freshness | Meaning | Action |
|---|---|---|
| `no_recorded_issue` + `metadata_match` | indexed and metadata-current | use graph with its best-effort caveat; confirm shipped claims from the symbol source |
| `parse_partial` | some ranges may be missing | inspect the flagged ranges directly |
| `excluded` / `not_indexed` | absent by policy | direct-search/read the exact source; re-index only if graph relationships are needed |
| `metadata_changed` / missing freshness | source and graph may diverge | re-index or qualify and confirm directly |

Absence of a recorded issue is not proof of completeness.

## Truncation rules

- `search_graph`: honor `total` and `has_more`; page or narrow.
- `trace_path`: honor `truncated` and resume with its cursor.
- `search_code`: compare returned results with `total_results`/raw matches; narrow when needed.
- `get_code_snippet`: honor `source_clipped` and read the omitted source range only if relevant.

Negative or exhaustive claims require complete pagination plus coverage for the claimed scope.

## Fast-index test caveat

Index mode decides test coverage: `full` covers tests (cite graph edges only after `check_index_coverage` shows no_recorded_issue + metadata_match); `fast` excludes tests by pattern (read them directly). Search the excluded test file directly, read the named test block, and label it as direct-source evidence.

## Required use-time block

Every foundation leaf includes a compact **Full view (memory graph)** section with:

- graph project, root, branch, commit, mode, nodes/edges;
- known exclusion/coverage caveats;
- the calls to rerun before porting: `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`.

The section points back to the graph; it does not paste architecture output into the skill.

## Failure modes

- **Duplicate index:** verify canonical name/root before indexing.
- **Stale snapshot:** compare graph HEAD and source HEAD.
- **First-page certainty:** detect truncation.
- **Degree worship:** high fan-in does not make a primitive reusable.
- **Manual-first browsing:** do not read directories or large files before graph discovery names the uncertainty.
- **Frozen skill:** rerun the live graph before reuse and re-confirm moved symbols.

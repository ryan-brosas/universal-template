---
name: openproject-foundation
description: "Use when porting OpenProject's service-object mutation spine — result objects with dependent trees, contract-gated stage ladders, transactional/advisory-locked execution contexts, field-level permission-reduced writability, system-vs-user change attribution, and the work-package attribute/update cascade. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval."
---
# OpenProject: mutation-kernel foundation

## Use this for
Use when porting OpenProject's service-object mutation spine — result objects with dependent trees, contract-gated stage ladders, transactional/advisory-locked execution contexts, field-level permission-reduced writability, system-vs-user change attribution, and the work-package attribute/update cascade. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `references/service-result-aggregation.md` — one combined outcome for composed services without exceptions.
- `references/base-callable-state-pipeline.md` — argument normalization plus shared side-channel state threading.
- `references/contracted-stage-ladder.md` — ordered success-gated validate → transform → persist pipeline.
- `references/transactional-service-context.md` — rollback-by-result-value, advisory-lock serialization, execute-as-user.
- `references/writable-attribute-permission-reduction.md` — declarative writable surface reduced by conditions then per-user permissions.
- `references/changed-by-system-attribution.md` — distinguishing user-caused from calculated changes in one pass.
- `references/wp-derived-attribute-plane.md` — param-plane ordering, date/duration derivation algebra, semantic-id move safety.
- `references/wp-update-cascade-consolidation.md` — fanning out while saving each record once (one journal entry).

## Capsule map
- **Result aggregation** — `service-result-aggregation`: ServiceResult tree; AND-success merge via merge!/add_dependent!; failure-default constructor; bind/map/on_success short-circuiting.
- **Callable envelope** — `base-callable-state-pipeline`: BaseCallable call→perform, trailing-options deep-symbolize, around_call state assignment, SubclassResponsibilityError guard.
- **Stage ladder** — `contracted-stage-ladder`: BaseContracted perform order (validate_params → before_perform → validate_contract → after_validate → persist → after_persist → after_perform), convention-named contracts type-checked against BaseContract.
- **Execution context** — `transactional-service-context`: transaction wrapping every run, ActiveRecord::Rollback on failed results, `mutex_on_<Class>_<id>` advisory lock, User.execute_as + notification scope.
- **Field-level authz** — `writable-attribute-permission-reduction`: attribute DSL registries, `_id` canonicalization, fail-closed any-of permission reduction, WP readonly-status narrowing to status-only.
- **Change attribution** — `changed-by-system-attribution`: change_by_system snapshot-delta wrapper; value-comparison so user overwrites of defaults stay attributed to the user.
- **WP attributes** — `wp-derived-attribute-plane`: attachments→versions→static→calculated(system)→custom(user) plane ordering; duration/due_date/start_date presence-then-absence derivation; same-UPDATE semantic-id clearing on project moves.
- **Update cascade** — `wp-update-cascade-consolidation`: per-id consolidation folding dependent changes into one master before a single `save(validate: false)`; in-memory semantic-id block assignment.

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
OpenProject (GPL-3.0), `dev@9579995645b707626b8de36fbaf33dfda6c04b9e`; Codebase Memory project `openproject` (FULL mode, 116023 nodes / 385322 edges, gen 2026-08-25T20:01:07Z; skipped=0; 90 parse_partial files all outside cited paths; vendor/tmp/images excluded by design). Pass 1 mined the mutation kernel only.

## Full view (memory graph)
Revalidate `openproject` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims. Note: Rails dynamic dispatch means class-level nodes (`WorkPackages::UpdateService`) carry no CALLS edges — trace method-level qualified names instead.

## Boundaries
Adopt the pure kernel contracts: result aggregation algebra, stage-ladder ordering, rollback-on-failure semantics, writable-reduction algorithm, change attribution, consolidation-before-save. Adapt lock primitive, calendar/working-days, permission predicates, and identifier schemes to the host. Omit Redmine-lineage glue (Disposable::Twin twins, Setting globals, journal-notification coupling) unless porting those subsystems too.

<!-- Preserved from the pre-foundation-skill-v1 loader. Detail remains historical and revision-pinned. -->


# pydantic: Foundation

## Use this for
Use when porting pydantic-v2-style machinery into another codebase: metaclass-driven model class construction, deferred/lazy validator+serializer builds with loud mock errors, generic-model parametrization and caching, union→tagged-union conversion, core-schema traversal/cleaning, or a type-checker plugin that synthesizes fields-aware constructors. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `./metaclass-two-branch-new.md` — which setup runs only for BaseModel subclasses vs BaseModel itself, and the namespace-before-type.__new__ ordering boundary.
- `./inspect-namespace-candidates.md` — field/private/ignored classification rules before the class exists, plus the delete-private-attrs-from-namespace invariant.
- `./complete-model-class-order.md` — post-fields completion ordering (schema → computed fields → deprecated descriptors → validator/serializer → lazy signature → flag) and mocks-on-failure degradation.
- `./private-attrs-post-init-wrap.md` — per-instance private defaults with validated-data-aware factories; conditional `model_post_init` wrapping only when privates exist.
- `./mock-valser-lazy-rebuild.md` — placeholder validator/serializer/core-schema proxies that attempt rebuild on first use then raise `class-not-fully-defined`.
- `./create-generic-submodel.md` — minting parametrized subclasses through `prepare_class`, slots forwarding, and pickle-safe global registration.
- `./generic-two-stage-cache.md` — early/late cache-key pair making `Model[List[T]][int] == Model[List[int]]` over a WeakValueDictionary.
- `./replace-types-substitution.md` — identity-preserving recursive TypeVar substitution incl. Annotated/union/model special forms.
- `./generic-recursion-self-type.md` — contextvar seen-set yielding recursive-ref placeholders for self-referential generics.
- `./apply-discriminator-conversion.md` — inferring literal tag values per choice and rewriting unions into tagged unions with nullable bookkeeping.
- `./deferred-discriminator-metadata.md` — two-phase mark-in-metadata / apply-during-clean handshake needing whole-graph definitions.
- `./schema-gather-visited-spans.md` — id-keyed span memoization marking refs non-inlinable without exponential re-traversal.
- `./core-utils-ser-schema-guards.md` — schema-kind partition sets and the function-schema→SerSchema fallback recursion.
- `./mypy-transform-pipeline.md` — plugin collect→defer→synthesize→persist pipeline writing metadata as the inheritance channel.
- `./mypy-add-method-injection.md` — shadow-don't-delete synthetic method insertion with unconflict-able `__pydantic_self__`.
- `./mypy-create-model-hook.md` — dynamic-class hook resolving `__base__` across three type shapes with a type[Self] escape hatch.
- `./mypy-plugin-config-cache.md` — config dict as mypy cache key; bump module `__version__` to invalidate plugin caches.
- `./mypy-field-default-extraction.md` — pure-AST has_default/alias/strict extraction from `Field(...)` calls.
- `./collect-fields-lenient-annotations.md` — lenient field collection: unevaluated hints defer via `_complete=False`, parent FieldInfo reuse, deprecated-method identity reset, post-collection delattr.
- `./field-info-annotated-attribute-merge.md` — Annotated↔assignment metadata merge order (assignment PREPENDED), final⇒frozen, FastAPI-subclass identity hack.
- `./rebuild-fields-nonmutating-replay.md` — deferred completion replays original (annotation, assignment) into NEW FieldInfo; strict mode eval→replace_types→eval.
- `./alias-generator-priority-gate.md` — generator applies only at alias_priority ≤1/unset slots; generated aliases stamped priority 1 so child generators re-run over parent fields.
- `./decorator-infos-mro-rebind.md` — MRO decorator collection with copy-on-rebind; bare parents stay unstamped; unwrapped methods replaced only on owned classes.
- `./signature-parameter-merge-ladder.md` — custom-init-first signature merge; var_kw-gated field fill-in; alias→validation_alias→name naming; `<factory>` sentinel; extra_data uniquening.
- `./protected-namespace-conflict-gate.md` — warn-vs-raise split for protected_namespaces collisions keyed on whether the base member is itself an inherited model field.
- `./descriptor-proxy-transparent-binding.md` — PydanticDescriptorProxy two-branch `__get__`, dunder forwarding, setter/deleter re-wrap with `wrapped_property` sync, signature-based implicit classmethod promotion.
- `./field-validator-annotated-promotion.md` — `@field_validator` infos converted via `_mode_to_validator[mode]._from_decorator` and appended to the annotation stream; defaults wrap last; v1 shims separate.
- `./model-validator-inner-outer-split.md` — before-inside/after-outside model-validator partitioning with pop-restore-ref discipline at both application points.
- `./validate-call-deferred-wrapper.md` — ValidateCallWrapper ArgsKwargs single-value validation, partial schema-vs-naming split, defer_build first-call gate, awaited-return validation.
- `./typeadapter-lazy-core-attrs.md` — caller-frame namespace capture with typing-proxy hop-back, reuse-then-generate attr ladder, tri-state rebuild.
- `./dataclass-fields-collection-twin.md` — define-once MRO filter over inherited `__dataclass_fields__`, init_var gates, non-mutating replay rebuild.
- `./mock-installer-rebuild-closure.md` — shared attempt-rebuild closure across model/dataclass/TypeAdapter mock installers; `is not False` fetch contract and depth-5 stacking.
- `./annotated-metadata-collection-partition.md` — Annotated metadata split into known-constraint dict vs opaque remainder; GroupedMetadata flattening; FieldInfo copy-before-clear; None-drop tail.
- `./constraint-application-ladder.md` — four-rung constraint→schema ladder (direct key-set / str wrap-chain / after-validator+js-stamp / RuntimeError); None return means unknown → original schema.
- `./single-annotation-schema-shape-branches.md` — shape dispatch before constraints: FieldInfo recursion, nullable pass-through, MISSING-sentinel union filtering, ref cloning under `_{repr(metadata)}` with def dedup.
- `./config-wrapper-precedence-ladder.md` — bases→namespace→kwargs config merge with pop-on-consume, config-both gate, deferred both-false alias check, core-config key renames.
- `./ns-resolver-frame-stack.md` — push/pop type frame stack for forward-ref evaluation; ascending-priority locals ending in the type's own name; dual cache invalidation.

## Capsule map
- **Model class construction** — `metaclass-two-branch-new`: bases-empty branch detects BaseModel creation; subclasses run full pipeline with `__pydantic_complete__=False` first.
- **Model class construction** — `inspect-namespace-candidates`: value-then-name classification ladder producing candidates lists in body order; explicit private attrs deleted from namespace.
- **Model class construction** — `complete-model-class-order`: fixed completion order; every failure path installs mocks and returns False instead of half-building.
- **Model class construction** — `private-attrs-post-init-wrap`: privates init via pydantic-core-called hook; wrap-or-substitute `model_post_init` only when `__private_attributes__` non-empty.
- **Deferred builds** — `mock-valser-lazy-rebuild`: MockValSer/MockCoreSchema attempt rebuild at first attribute access; two-step getattr preserves AttributeError semantics before the coded user error.
- **Generics** — `create-generic-submodel`: metaclass-kwarg metadata + prepare_class + conditional global registration for picklable parametrizations.
- **Generics** — `generic-two-stage-cache`: cheap early key + exact late key with union-ordering discriminator; single-typevar unwrapped extra entry.
- **Generics** — `replace-types-substitution`: recursive substitution preserving object identity on no-change; Any absorbs unions; PEP-604 rebuilt by reduce(or_).
- **Generics** — `generic-recursion-self-type`: add-before-yield/remove-after-yield ContextVar set; second sighting yields PydanticRecursiveRef.
- **Discriminated unions** — `apply-discriminator-conversion`: stack-based choice coalescing; literal-only tag inference; shared alias enforcement; nullable re-wrap condition.
- **Discriminated unions** — `deferred-discriminator-metadata`: internal metadata marker harvested by the clean pass once definitions exist.
- **Core schema tooling** — `schema-gather-visited-spans`: visited spans of encountered refs replay non-inlinable marks; end=None is the in-progress cycle guard.
- **Core schema tooling** — `core-utils-ser-schema-guards`: predicate sets partitioning fields/functions/list-like schemas; as_ser_schema fallback for plain/wrap collisions.
- **mypy plugin** — `mypy-transform-pipeline`: defer on placeholder types BEFORE synthesis; serialized metadata under one METADATA_KEY drives subclass collection.
- **mypy plugin** — `mypy-add-method-injection`: plugin_generated cleanup, unique-redefinition shadowing, Decorator-wrapped classmethod nodes.
- **mypy plugin** — `mypy-create-model-hook`: __base__ resolution across TypeInfo/Var-Instance/type[Self]; nested-class fullname '@' republish quirk.
- **mypy plugin** — `mypy-plugin-config-cache`: report_config_data return value participates in cache keys; unknown config warns, wrong types raise.
- **mypy plugin** — `mypy-field-default-extraction`: TempNode/EllipsisExpr sentinels and validation_alias-over-alias precedence from raw AST.
- **Fields & metadata plane** — `collect-fields-lenient-annotations`: collect-never-raises; `_original_annotation`/`_original_assignment` stored for replay; field attrs deleted off the class.
- **Fields & metadata plane** — `field-info-annotated-attribute-merge`: assignment metadata copied and PREPENDED before Annotated metadata (`_construct(prepend + metadata)`).
- **Fields & metadata plane** — `rebuild-fields-nonmutating-replay`: rebuild returns a fresh dict; strict double-eval (eval → replace_types → eval) resolves stringified generics.
- **Fields & metadata plane** — `alias-generator-priority-gate`: explicit alias (priority ≥2) beats generator; generated aliases are priority-1 so inheritance re-generates them.
- **Fields & metadata plane** — `decorator-infos-mro-rebind`: bases walked via `mro(typ)[1:-1]` reversed, infos copied per rebind, `to_replace` setattr only on owned classes.
- **Fields & metadata plane** — `signature-parameter-merge-ladder`: init params first (minus `init=False`), fields appended KEYWORD_ONLY only through var_kw.
- **Fields & metadata plane** — `protected-namespace-conflict-gate`: base-member collision raises ValueError; otherwise warning with replacement-namespace suggestion.
- **Validation execution** — `descriptor-proxy-transparent-binding`: decorator proxies stay attribute-transparent while remaining type-detectable; `cls`-first functions auto-wrap in classmethod, `self`-first raise.
- **Validation execution** — `field-validator-annotated-promotion`: v2 field validators become Annotated-metadata validator objects applied through one annotation pipeline; wildcard `*` matches; defaults wrap outermost.
- **Validation execution** — `model-validator-inner-outer-split`: 'before' validators wrap inside the fields schema, others outside the serialized model; ref popped/restored per application.
- **Validation execution** — `validate-call-deferred-wrapper`: args validated as one ArgsKwargs value; partials unwrap for schema but not naming; defer_build defers to first call.
- **Validation execution** — `typeadapter-lazy-core-attrs`: frame-depth namespace capture (typing-proxy hop-back), reuse dunder core attrs unless mocks, tri-state rebuild.
- **Validation execution** — `dataclass-fields-collection-twin`: inherited `__dataclass_fields__` filtered by defining-base annotations so each field collects once; replay rebuild mirrors models.
- **Validation execution** — `mock-installer-rebuild-closure`: three mock installers share one closure factory keyed by (surface, rebuild entry point); handlers fetch on `is not False`.
- **Annotation & config plane** — `annotated-metadata-collection-partition`: total lossless split into (constraint dict, remainder); class-form metadata via vars(); FieldInfo copied before clearing; Nones dropped last.
- **Annotation & config plane** — `constraint-application-ladder`: direct key-set only inside the per-constraint allowed schema set; str-chain constraints wrap with use-time TypeError translation; unknowns return None, caller keeps the original.
- **Annotation & config plane** — `single-annotation-schema-shape-branches`: sentinel-union filtering never drops the sentinel; ref clones dedup by repr(metadata); unknown metadata returns the same object unmodified.
- **Annotation & config plane** — `config-wrapper-precedence-ladder`: kwargs popped so they never leak to the metaclass; alias/name patching happens at core-config time where both-false raises.
- **Annotation & config plane** — `ns-resolver-frame-stack`: pushed type's own name tops the locals for self-reference; cached namespace invalidated on both push and pop.

## Extending the foundation
Add one `./<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
pydantic (MIT), `main@2151025aa51263f3016502b00010b78e4481eaa1`; Codebase Memory project `pydantic` (full mode, 15,741n/94,471e, gen 2026-08-25T20:10Z generation_matches=true; head==base==pin zero drift; parse_partial ×2 confined to a Makefile line and a mypy fixture, neither cited). PROJECT MIGRATION: the 18 legacy capsules were mined against the now-retired twin project `ext-pydantic` at the SAME commit (identical node/edge counts) — their recorded Retrieve snippets are historical evidence; re-run them against `pydantic`. All capsules from the 2026-08-26 pass onward cite `pydantic` directly. Pass 2 (2026-08-26): +6 validation-execution capsules at the same pin (no re-index needed; counts unchanged). Pass 3 (2026-08-27): +5 annotation-application/config/namespace capsules at the same pin (git HEAD re-verified == pin, porcelain-clean; no re-index); MCP graph unavailable this session → direct source+test evidence chain, Retrieve snippets written but unexecuted.

## Full view (memory graph)
Revalidate `pydantic` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims. Pass 2026-08-26: all 7 newly cited paths verified `no_recorded_issue`+`metadata_match`; six new-capsule Retrieve calls executed byte-for-byte against `pydantic`. Tests are indexed (full mode): direct probes live in `tests/test_fields.py`, `tests/test_model_signature.py`, `tests/test_decorators.py`, and `tests/test_main.py` (`test_protected_namespace_*` :3064-3107); runner evidence: 24 passed / 0 failed under pydantic-core 2.48.0. Pass 2 2026-08-26: all 13 cited paths (8 source + 5 test) verified `no_recorded_issue`+`metadata_match`, generation-matched; six new Retrieve calls executed against `pydantic`; probe battery re-run GREEN (see work record verification.md pass 2). Pass 3 2026-08-27: Codebase Memory MCP NOT connected in-session — fallback evidence chain per AGENTS.md (direct full-file reads of `_known_annotated_metadata.py`, `_config.py`, `_namespace_utils.py`, `_generate_schema.py` ranges + direct test reads; 16/16 pytest probes GREEN under pydantic-core 2.48.0 venv); five new capsules' Retrieve snippets written but unexecuted (recorded as caveat); see work record verification.md pass 3.

## Boundaries
Adopt the pure contracts: construction ordering, lazy-build mock protocol, cache-key algebra, discriminator inference algorithm, span memoization, AST-extraction rules. Adapt error codes/messages, import-cycle plumbing (`import_cached_*`), frame-depth magic, and mypy-API specifics to your host. Omit pydantic-core Rust runtime behavior, JSON-schema emission, deprecated v1 shims (`pydantic/deprecated/*`, `pydantic/v1/*`), network types, and plugin interop with pydantic-settings beyond the documented arg surgery.

## Reference-file inventory

Every preserved capsule/reference file in this foundation:

- [`alias-generator-priority-gate.md`](./alias-generator-priority-gate.md)
- [`annotated-metadata-collection-partition.md`](./annotated-metadata-collection-partition.md)
- [`apply-discriminator-conversion.md`](./apply-discriminator-conversion.md)
- [`collect-fields-lenient-annotations.md`](./collect-fields-lenient-annotations.md)
- [`complete-model-class-order.md`](./complete-model-class-order.md)
- [`config-wrapper-precedence-ladder.md`](./config-wrapper-precedence-ladder.md)
- [`constraint-application-ladder.md`](./constraint-application-ladder.md)
- [`core-utils-ser-schema-guards.md`](./core-utils-ser-schema-guards.md)
- [`create-generic-submodel.md`](./create-generic-submodel.md)
- [`dataclass-fields-collection-twin.md`](./dataclass-fields-collection-twin.md)
- [`decorator-infos-mro-rebind.md`](./decorator-infos-mro-rebind.md)
- [`deferred-discriminator-metadata.md`](./deferred-discriminator-metadata.md)
- [`descriptor-proxy-transparent-binding.md`](./descriptor-proxy-transparent-binding.md)
- [`field-info-annotated-attribute-merge.md`](./field-info-annotated-attribute-merge.md)
- [`field-validator-annotated-promotion.md`](./field-validator-annotated-promotion.md)
- [`generic-recursion-self-type.md`](./generic-recursion-self-type.md)
- [`generic-two-stage-cache.md`](./generic-two-stage-cache.md)
- [`inspect-namespace-candidates.md`](./inspect-namespace-candidates.md)
- [`metaclass-two-branch-new.md`](./metaclass-two-branch-new.md)
- [`mock-installer-rebuild-closure.md`](./mock-installer-rebuild-closure.md)
- [`mock-valser-lazy-rebuild.md`](./mock-valser-lazy-rebuild.md)
- [`model-validator-inner-outer-split.md`](./model-validator-inner-outer-split.md)
- [`mypy-add-method-injection.md`](./mypy-add-method-injection.md)
- [`mypy-create-model-hook.md`](./mypy-create-model-hook.md)
- [`mypy-field-default-extraction.md`](./mypy-field-default-extraction.md)
- [`mypy-plugin-config-cache.md`](./mypy-plugin-config-cache.md)
- [`mypy-transform-pipeline.md`](./mypy-transform-pipeline.md)
- [`ns-resolver-frame-stack.md`](./ns-resolver-frame-stack.md)
- [`private-attrs-post-init-wrap.md`](./private-attrs-post-init-wrap.md)
- [`protected-namespace-conflict-gate.md`](./protected-namespace-conflict-gate.md)
- [`rebuild-fields-nonmutating-replay.md`](./rebuild-fields-nonmutating-replay.md)
- [`replace-types-substitution.md`](./replace-types-substitution.md)
- [`schema-gather-visited-spans.md`](./schema-gather-visited-spans.md)
- [`signature-parameter-merge-ladder.md`](./signature-parameter-merge-ladder.md)
- [`single-annotation-schema-shape-branches.md`](./single-annotation-schema-shape-branches.md)
- [`typeadapter-lazy-core-attrs.md`](./typeadapter-lazy-core-attrs.md)
- [`validate-call-deferred-wrapper.md`](./validate-call-deferred-wrapper.md)

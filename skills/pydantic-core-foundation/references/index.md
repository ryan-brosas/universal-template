<!-- Preserved from the pre-foundation-skill-v1 loader. Detail remains historical and revision-pinned. -->

# pydantic-core: validation & serialization engine foundation

## Use this for
Use when porting schema-driven validation/serialization machinery, embedding pydantic-style validators in another runtime, or answering "what does pydantic-core guarantee" questions about unions, recursion, defaults, error locations, and field serialization. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `./schema-dispatch-buildvalidator.md` — how `{"type": ...}` dicts become validator structs, incl. prebuilt reuse and SchemaError wrapping.
- `./schema-validator-entrypoints.md` — public validate/isinstance/get_default_value contracts over one generic input funnel.
- `./validation-state-scoped-rebind.md` — thread-through state knobs with RAII scoped mutation and exactness flooring.
- `./smart-union-best-match.md` — smart-mode ranking (fields_set_count → exactness), instant-exact short-circuit, error-volume rule.
- `./tagged-union-discriminator.md` — discriminator lookup across dict/object/JSON planes; NotFound vs Invalid taxonomy.
- `./definitions-refs-lifecycle.md` — ref slots fill-once via Arc<OnceLock>, Weak refs break cycles, three build errors.
- `./recursion-guard-cyclic-inputs.md` — two-key identity cycle detection, platform depth limits, array→set promotion.
- `./model-fields-ladder.md` — per-field alias/name resolution, default ladder, extras handling, output triple.
- `./defaults-with-default-contract.md` — copy_default hash probe, on_error ladder, DefaultFactoryNotCalled gate.
- `./function-validators-ordering.md` — before/after/plain/wrap execution order plus exception conversion table.
- `./error-plumbing-reversed-location.md` — reversed-location push-prefix pattern and ValError four-variant taxonomy.
- `./schema-serializer-mirror.md` — serializer tree mirroring validators; per-call SerializationState; JSON-size heuristic.
- `./general-fields-serialization-order.md` — input-order preservation, five skip reasons, strict required-count gate.
- `./infer-serialization-obtype.md` — ObType classify-then-dispatch for schema-less serialization; divergent recursion policy.
- `./lookup-key-alias-resolution.md` — alias grammar (string | list | path-lists) across dict/mapping/attr/JSON backends.
- `./input-type-triad-dual-dispatch.md` — one `Input` trait + `InputType{Python,Json,String}` tag; strict/lax convention and exact_int/exact_str defaults.
- `./validate-json-funnel-error-mapping.md` — str/bytes/bytearray coercion ladder, single jiter parse, JsonInvalid mapped onto the original input.
- `./json-validator-text-contract.md` — `"json"` schema type consumes text RELATIVE to input kind; Any-collapse PythonParse fast path; double-encoding trap.
- `./json-value-coercion-ladder.md` — per-scalar strict/lax conversion table with exactness labels; arrays back tuple/set/frozenset.
- `./allow-partial-last-element.md` — one-item lookahead marks last element; its errors drop, earlier errors raise; works over python AND json.
- `./borrow-input-collection-gats.md` — BorrowInput owned/borrowed duality, per-backend GAT views, ConsumeIterator consumers, Never filler.
- `./json-duplicate-key-dedup.md` — jiter keeps duplicates; lookup last-wins free, as_kwargs dedups backwards keeping document order.
- `./cache-strings-config-plane.md` — where does string interning get configured, and which producers opt OUT.
- `./datetime-numeric-twins.md` — how do int/float timestamps become datetimes vs times-of-day, and where does `val_temporal_unit` apply.
- `./generic-py-mapping-tri-dispatch.md` — how do dict / Mapping / from-attributes inputs share one field-lookup path, and what does `last_key` do when it can't.
- `./model-instance-fast-path-revalidate.md` — what happens when you validate an EXISTING model instance, and why does constructing a new one floor exactness to Strict.
- `./self-instance-validate-init.md` — how does validation populate a CALLER-CONSTRUCTED model instance instead of building one.
- `./string-mode-mapping-duality.md` — what IS an input under `validate_strings`.
- `./val-json-bytes-ladder.md` — how does a bytes field decode from JSON text, and why does base64 accept BOTH alphabets.
- `./validate-strings-funnel.md` — does `strict=True` stop string→scalar coercion in string mode.

## Capsule map
- **Build & dispatch** — `schema-dispatch-buildvalidator`: macro match on EXPECTED_TYPE consts; base-vs-nested entry points gate prebuilt reuse; build failures are SchemaError with type prefix.
- **Public surface** — `schema-validator-entrypoints`: isinstance maps LineErrors→False but propagates Omit/UseDefault/InternalErr; fresh ValidationState per call keeps validators shareable.
- **Validation state** — `validation-state-scoped-rebind`: readonly Extra rebinds via drop-guard scopes; mutable metrics live on ValidationState; floor_exactness is monotone; defaults ladder override→schema→builtin.
- **Union engines** — `smart-union-best-match`: fields_set_count primary / exactness tiebreak, leftmost wins ties, stop recording errors after first success. `tagged-union-discriminator`: tag read before dispatch through LookupKey; missing vs invalid tags are distinct errors carrying expected-tags repr.
- **Recursion & refs** — `definitions-refs-lifecycle`: fill-once definition slots, weak refs from users, never-filled/duplicate-ref build failures, `"..."` recursion-safe lazy names. `recursion-guard-cyclic-inputs`: (obj_id,node_id) set catches cyclic INPUT data → recursion_loop error; hard u8 depth ceiling 255/99/49 by platform; inline 16-slot stack promotes to hashset.
- **Structured types** — `model-fields-ladder`: LookupKeyCollection.select(by_alias,by_name) → validate-or-default per field; extras validatable as keys+values only under allow; returns (dict, extra|None, fields_set) in canonical names; assignment deletes the key before validating (V1 behavior).
- **Defaults** — `defaults-with-default-contract`: unhashable default ⇒ deepcopy each use (decided at build); on_error raise/omit/default with UseDefault taking precedence; data-taking factories refused after field errors.
- **Python hooks** — `function-validators-ordering`: before=py-first, after=inner-first, plain=replaces, wrap=user-driven handler with metric sync-back; PydanticOmit/PydanticUseDefault/PydanticCustomError convert at one choke point.
- **Errors** — `error-plumbing-reversed-location`: locations stored reversed so unwinding pushes outer items; LineError order is iteration order; input snapshots taken at creation.
- **Serialization** — `schema-serializer-mirror`: CombinedSerializer tree over shared Definitions; warnings accumulate to a terminal final_check; expected_json_size AtomicUsize caches buffer hint; __reduce__ rebuilds from original schema. `general-fields-serialization-order`: output follows INPUT order; None serializer = exclude; strict required-count check suppressed whenever exclusions active. `infer-serialization-obtype`: ObType dispatch with subclass upcasting; cycles raise in Json mode but return-as-is in Python mode.
- **Alias plumbing** — `lookup-key-alias-resolution`: Simple/Choice/PathChoices grammar resolved identically over dict.get, mapping.get, getattr chains, and reversed jiter scans (last-dup-wins).
- **Input & ingestion** — `input-type-triad-dual-dispatch`: one generic `Input` trait over `InputType{Python,Json,String}`; validators request backend-typed views, never downcast; exactness-labeled matches feed union ranking. `validate-json-funnel-error-mapping`: str/bytes/bytearray → single jiter parse → JsonInvalid carries jiter line/col text but points at the caller's input. `json-validator-text-contract`: `"json"` means "parse one MORE layer of text from here" — top-level json schemas need double encoding under validate_json (json_type rejection of parsed values); Any-inner returns raw parsed object with inf/nan allowed and dup keys kept. `json-value-coercion-ladder`: JSON str is strict-not-exact ("string is a converting input"), Int→float strict-not-exact, arrays serve tuple/set/frozenset as strict-never-exact, decimal from float is string-mediated. `allow-partial-last-element`: per-element flag flip via one-item lookahead; last-element LineErrors silently dropped, earlier errors raise; input-kind independent. `borrow-input-collection-gats`: BorrowInput re-borrows owned-or-borrowed iterator items; ValidatedDict/List/Tuple/Set GAT views + ConsumeIterator consumers + uninhabited Never filler. `json-duplicate-key-dedup`: parser keeps duplicates — field lookup last-wins naturally, kwargs conversion dedups backwards preserving document order.
- **cache_strings plane** — `cache-strings-config-plane`: where does string interning get configured, and which producers opt OUT.
- **datetime numeric twins** — `datetime-numeric-twins`: how do int/float timestamps become datetimes vs times-of-day, and where does `val_temporal_unit` apply.
- **GenericPyMapping tri-dispatch** — `generic-py-mapping-tri-dispatch`: how do dict / Mapping / from-attributes inputs share one field-lookup path, and what does `last_key` do when it can't.
- **Model instance fast path** — `model-instance-fast-path-revalidate`: what happens when you validate an EXISTING model instance, and why does constructing a new one floor exactness to Strict.
- **self_instance / validate_init** — `self-instance-validate-init`: how does validation populate a CALLER-CONSTRUCTED model instance instead of building one.
- **String-mode mapping duality** — `string-mode-mapping-duality`: what IS an input under `validate_strings`.
- **val_json_bytes ladder** — `val-json-bytes-ladder`: how does a bytes field decode from JSON text, and why does base64 accept BOTH alphabets.
- **validate_strings funnel** — `validate-strings-funnel`: does `strict=True` stop string→scalar coercion in string mode.
## Extending the foundation
Add one `./<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
pydantic-core (MIT), `main@383eb95a19433754c0cecf7025b50c26b6d97a36`; Codebase Memory project `pydantic-core` (ready FULL 5,651n/40,594e at that pin = base_sha = live HEAD, zero drift; parse_partial ×1 Makefile only; no stale twin). History: first 15 capsules were mined under project name `ext-pydantic-core`, which later vanished from the registry; pass-1 of the FAC-251 lane re-indexed the identical checkout as `pydantic-core` and verified head==base==pin before citing new seams.

## Full view (memory graph)
Revalidate `pydantic-core` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims. BM25 plane re-verified live this pass at the same pin under the new project name (validate_json funnel rank-1 :248-281; enumerate_last_partial :90; JsonValue.validate_* block line-exact; map_json_err :113). Rust source: run probes from repo root (`src/...` paths); Python test suite runs with `PYTHONPATH=python` after building `_pydantic_core` (`cargo build --release`, copy `target/release/lib_pydantic_core.so` → `python/pydantic_core/_pydantic_core.abi3.so`) — pytest needs `-c /dev/null` because pyproject addopts require pytest-benchmark/timeout plugins AND conftest needs hypothesis/dirty_equals/inline_snapshot. Runner evidence @ pin: cargo release build green; test_union 83p+1xf; definitions+recursive+with_default+function+tagged_union 283p+2xf; model_fields+test_errors+test_json 551p+2s; serializers test_model+test_any 166p+2s; pass-1 ingestion-plane probes P1–P8 executed green against the prebuilt abi3 module while full-suite collection was dependency-blocked (see work record).

## Boundaries
Adopt pure contracts: dispatch table shape, union ranking algebra, ref-slot lifecycle, recursion guard semantics, reversed-location error envelope, ordering contracts for function validators, serialization skip-priority and order rules. Adapt host integration: pyo3 pyclass plumbing, GIL/critical-section usage, jiter-specific JSON scanning, pickle reconstruction via Python schema retention. Omit product surfaces: URL parser internals (`src/url.rs`), string-constrained validators' regex engine choices, benchmark harness, wasm/emscripten runner, and CI/build tooling (`build_tools.rs` beyond SchemaError).

## Reference-file inventory

Every preserved capsule/reference file in this foundation:

- [`allow-partial-last-element.md`](./allow-partial-last-element.md)
- [`borrow-input-collection-gats.md`](./borrow-input-collection-gats.md)
- [`cache-strings-config-plane.md`](./cache-strings-config-plane.md)
- [`datetime-numeric-twins.md`](./datetime-numeric-twins.md)
- [`defaults-with-default-contract.md`](./defaults-with-default-contract.md)
- [`definitions-refs-lifecycle.md`](./definitions-refs-lifecycle.md)
- [`error-plumbing-reversed-location.md`](./error-plumbing-reversed-location.md)
- [`function-validators-ordering.md`](./function-validators-ordering.md)
- [`general-fields-serialization-order.md`](./general-fields-serialization-order.md)
- [`generic-py-mapping-tri-dispatch.md`](./generic-py-mapping-tri-dispatch.md)
- [`infer-serialization-obtype.md`](./infer-serialization-obtype.md)
- [`input-type-triad-dual-dispatch.md`](./input-type-triad-dual-dispatch.md)
- [`json-duplicate-key-dedup.md`](./json-duplicate-key-dedup.md)
- [`json-validator-text-contract.md`](./json-validator-text-contract.md)
- [`json-value-coercion-ladder.md`](./json-value-coercion-ladder.md)
- [`lookup-key-alias-resolution.md`](./lookup-key-alias-resolution.md)
- [`model-fields-ladder.md`](./model-fields-ladder.md)
- [`model-instance-fast-path-revalidate.md`](./model-instance-fast-path-revalidate.md)
- [`recursion-guard-cyclic-inputs.md`](./recursion-guard-cyclic-inputs.md)
- [`schema-dispatch-buildvalidator.md`](./schema-dispatch-buildvalidator.md)
- [`schema-serializer-mirror.md`](./schema-serializer-mirror.md)
- [`schema-validator-entrypoints.md`](./schema-validator-entrypoints.md)
- [`self-instance-validate-init.md`](./self-instance-validate-init.md)
- [`smart-union-best-match.md`](./smart-union-best-match.md)
- [`string-mode-mapping-duality.md`](./string-mode-mapping-duality.md)
- [`tagged-union-discriminator.md`](./tagged-union-discriminator.md)
- [`val-json-bytes-ladder.md`](./val-json-bytes-ladder.md)
- [`validate-json-funnel-error-mapping.md`](./validate-json-funnel-error-mapping.md)
- [`validate-strings-funnel.md`](./validate-strings-funnel.md)
- [`validation-state-scoped-rebind.md`](./validation-state-scoped-rebind.md)

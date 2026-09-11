<!-- Preserved from the pre-foundation-skill-v1 loader. Detail remains historical and revision-pinned. -->


# ell: Language Model Programming Foundation

## Use this for
Use when building prompt-to-program frameworks that must version prompts as code (lexical closures + content hashes), trace which model call produced which text fragment through arbitrary string mutations (`_lstr` origin traces), adapt one call pipeline to many vendor APIs behind a validation-enforced provider interface, or persist/version LLM programs and invocations in SQLite/Postgres with alembic. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `./lmp-decorator-pipeline.md` — How does a plain function become a tracked, provider-calling LMP?
- `./lstr-origin-trace-propagation.md` — How do I keep provenance on text through concatenation, formatting, slicing, joins and arbitrary str methods?
- `./lstr-pydantic-roundtrip-schema.md` — How does a str subclass survive pydantic serialization without losing its metadata?
- `./content-block-single-field-coercion.md` — How do heterogeneous inputs become validated single-payload content blocks?
- `./message-tool-call-result-plane.md` — How do tool calls ride inside messages and get executed into follow-up messages?
- `./tool-decorator-params-model.md` — How do I synthesize a typed JSON schema for a tool from its signature?
- `./tool-result-content-block-envelope.md` — What exact shape does an invoked tool return, per result type?
- `./provider-call-lifecycle-validation.md` — Where is the single choke point every provider call passes through, and what does it assert?
- `./openai-stream-default-and-retraction.md` — Why does ell stream by default and when does it silently stop?
- `./anthropic-role-collapse-and-stream-reassembly.md` — How are alternating roles collapsed and streamed blocks reassembled for Anthropic?
- `./bedrock-converse-provider-dual.md` — How does one provider class serve both converse and converse_stream?
- `./provider-registry-configurator.md` — How do clients map to providers and models to clients at call time?
- `./lexical-closure-recursion.md` — How is a function's full dependency source extracted as standalone code?
- `./closure-hash-and-versioning.md` — What exactly is hashed into an LMP version id, and when?
- `./should-import-boundary.md` — When is a dependency emitted as an import versus inlined as source?
- `./track-invocation-stack.md` — How are nested LMP calls linked into parent-child invocation trees across threads?
- `./state-cache-key.md` — What identity makes one LMP invocation cache-equivalent to another?
- `./invocation-blob-externalization.md` — When do invocation payloads move out of the row into blob storage?
- `./sqlstore-idempotent-writes.md` — Why can concurrent writers never duplicate versions or corrupt counts?
- `./migrations-three-case-bootstrap.md` — How does a fresh, pre-alembic, or stale database converge to head safely?
- `./autocommit-diff-commit-message.md` — How does the library write commit messages for prompt changes using itself?
- `./evaluation-run-pipeline.md` — How do dataset expansion, API batching, and labeler invocation interleave with persistence?
- `./evaluation-persistence-labeler-ids.md` — How do evaluation versions, runs, and labels get deterministic identity?
- `./verbosity-renderer-and-phone-home.md` — What does the verbose logging plane actually do at call time — including the outbound network request a porter must know about?
- `./studio-db-watcher.md` — How does the UI learn about new invocations without polling the database contents?

## Capsule map
- **Decorator pipeline** — `lmp-decorator-pipeline`: prompt-first execution + strict dunder/3-tuple wrapper contract; docstring-as-system only for string-returning prompts; param merge config < decorator < call.
- **Traced strings** — `lstr-origin-trace-propagation`: `_lstr(str)` carries a frozenset of origin ids; every mutating operation unions operand traces; indexing deliberately nulls logits but keeps origins.
- **Traced strings** — `lstr-pydantic-roundtrip-schema`: `__get_pydantic_core_schema__` serializes `_lstr` as a tagged dict `{content, __origin_trace__, __lstr: True}` with a json-or-python validator so plain strs coerce back in.
- **Message model** — `content-block-single-field-coercion`: `ContentBlock` allows exactly one non-null payload field among six; images coerce from URL/base64/numpy/PIL with mode normalization.
- **Message model** — `message-tool-call-result-plane`: `ToolCall.__call__` forbids kwargs (params live on the call), executes the bound tool, and `call_tools_and_collect_as_message` returns a user-role Message ready to append.
- **Tools** — `tool-decorator-params-model`: signature inspection builds a pydantic `create_model` (`FieldInfo` defaults preserved); untyped parameters raise instead of guessing; schema flows to providers via `model_json_schema()`.
- **Tools** — `tool-result-content-block-envelope`: wrapper always returns `(result, api_params, {})`; with a `_tool_call_id` the result becomes a `ToolResult`, parsed blocks degrade to text, tool_call/audio payloads assert-refused.
- **Provider SPI** — `provider-call-lifecycle-validation`: `Provider.call` asserts disallowed params absent, validates translated params against the client's real signature, and (unless `dangerous_disable_validation`) asserts every returned text is an `_lstr` carrying the current origin id.
- **Provider SPI** — `openai-stream-default-and-retraction`: stream=True + include_usage is injected by default and retracted when tools/response_format/`supports_streaming=False`; response-format-as-class switches endpoint to `beta.chat.completions.parse`.
- **Provider SPI** — `anthropic-role-collapse-and-stream-reassembly`: consecutive same-role messages merge before sending; system pops off the front; streaming rebuilds blocks by index with partial-JSON accumulation and drops unparseable tool args.
- **Provider SPI** — `bedrock-converse-provider-dual`: `provider_call_function` consumes the `stream` key and swaps between `converse`/`converse_stream`; system message wraps as `[{'text': ...}]`; tools nest under `toolSpec`/`toolConfig`.
- **Provider SPI / config** — `provider-registry-configurator`: registry keyed by client *type* (issubclass match), models keyed by name with fallback flag; thread-local override stack lets tests shadow the global registry; unknown models fall back to default OpenAI client with a warning.
- **Versioning** — `lexical-closure-recursion`: depth-first closure pulls globals/frees via dill, recurses through callables/classes/modules, extracts only referenced module attributes, marks mutable values `<BmV>`, dedupes and Black-formats.
- **Versioning** — `closure-hash-and-versioning`: version id = md5(black(source) + cleaned deps + qualname) prefixed `lmp-`; eager under `lazy_versioning=False`, else deferred until first tracked call; version numbers come from max(existing)+1 keyed by FQN.
- **Versioning** — `should-import-boundary`: site-packages and `ell.*` become import lines; project-root/local modules inline their source; two divergent implementations exist (closure.py uses `util.closure_util.should_import`, not `util/should_import.py`) — port the one your entry path actually imports.
- **Tracking** — `track-invocation-stack`: thread-local stack assigns each tracked call a random id; children read the top of the stack as `used_by_id`; pop happens in `finally` so failed calls still unwind.
- **Tracking** — `state-cache-key`: sha256 of serialized params JSON + sorted immutable globals/free vars; cache hit deserializes stored results instead of calling the model; key computed pre-call when caching, post-call otherwise.
- **Persistence** — `invocation-blob-externalization`: contents >102400 bytes externalize to gzip blobs only when a blob store exists; the row keeps just `(invocation_id, is_external=True)`.
- **Persistence** — `sqlstore-idempotent-writes`: `write_lmp` checks-then-inserts with IntegrityError rollback (race-tolerant), skips unknown use ids silently, and increments `num_invocations` inside `write_invocation`'s transaction.
- **Persistence** — `migrations-three-case-bootstrap`: table-set intersection decides stamp-vs-create-vs-upgrade; v1 databases (no eval tables) stamp the initial revision, others head; empty DBs `create_all` then stamp head.
- **Versioning** — `autocommit-diff-commit-message`: autocommit generates a ≤10-word LLM commit message from old-vs-new closure diff (BV/BmV tags stripped first) using `@ell.simple(config.autocommit_model)` — dogfooding with `exempt_from_tracking=True` to break recursion.
- **Evaluations** — `evaluation-run-pipeline`: dataset XOR n_evals enforced; batching folds repetition into api param `n`, otherwise duplicates datapoints; two-phase executor writes intermediates then labels; verbose flag temporarily overrides global config.
- **Evaluations** — `evaluation-persistence-labeler-ids`: evaluation id = md5 over dataset hash + sorted labeler LMP hashes; labeler ids are parseable `labeler-<eval>-<name>-<TYPE>` strings; every label carries the labeling invocation id.
- **Studio** — `studio-db-watcher`: file stat polling (mtime/size/inode) broadcasts `database_updated` over websockets; deletion also notifies; production serves SPA with index.html fallback.
- **Verbosity / telemetry** — `verbosity-renderer-and-phone-home`: char-counter stream wrapping for terminal rendering; one-shot version ping to `version.ell.so` on first logged call — porters must consciously keep or strip it.

## Extending the foundation
Add one `./<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
ell (MIT), `main@9d129846203e75efeb4e5cddd3fb1c164dc0b243`; Codebase Memory project `ext-ell` (ready FULL, 2,289n/9,471e, gen 2026-08-23T09:41Z, generation_matches=true; parse_partial ×8 confined to docs/ramblings sketches + one realtime example + one minified studio component, none cited; not_indexed ×28 images by design). Python core ~8.2k LOC whole-file-read this pass; ell-studio React plane uncited (product shell).

## Full view (memory graph)
Revalidate `ext-ell` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Graph root `$REFERENCE_ROOT/external/ell`, branch main, HEAD==base==`9d129846` (zero drift at pass 1). BM25 indexes Function/Method tokens well (rank-1 line-exact on `_lstr.origin_trace`, `push_invocation`, `compute_state_cache_key`, `disallowed_api_params`, `init_or_migrate_database`) but has zero recall on bare config flags (`lazy_versioning`) and camelCase JS internals — fall back to grep on misses. Coverage stdin-JSON on all 29 cited paths returned `no_recorded_issue`+`metadata_match`. Source and direct tests decide shipped claims.

## Boundaries
Adopt the pure contracts: `_lstr` trace algebra, ContentBlock single-payload validation, params-model synthesis, provider call lifecycle assertions, closure hashing, state cache keys, three-case migration bootstrap. Adapt host-specific integrations: provider SDK translations (endpoint names drift per vendor release), SQLiteStore/SQLBlobStore layouts, the studio server routes. Omit source-specific transport/product behavior: the ell-studio React app, docs/ramblings sketches, x/openai_realtime example app, the outbound version-check ping in verbosity.py (a phone-home you probably don't want), and the deprecated `lm_params`/`set_store` shims.

## Reference-file inventory

Every preserved capsule/reference file in this foundation:

- [`anthropic-role-collapse-and-stream-reassembly.md`](./anthropic-role-collapse-and-stream-reassembly.md)
- [`autocommit-diff-commit-message.md`](./autocommit-diff-commit-message.md)
- [`bedrock-converse-provider-dual.md`](./bedrock-converse-provider-dual.md)
- [`closure-hash-and-versioning.md`](./closure-hash-and-versioning.md)
- [`content-block-single-field-coercion.md`](./content-block-single-field-coercion.md)
- [`evaluation-persistence-labeler-ids.md`](./evaluation-persistence-labeler-ids.md)
- [`evaluation-run-pipeline.md`](./evaluation-run-pipeline.md)
- [`invocation-blob-externalization.md`](./invocation-blob-externalization.md)
- [`lexical-closure-recursion.md`](./lexical-closure-recursion.md)
- [`lmp-decorator-pipeline.md`](./lmp-decorator-pipeline.md)
- [`lstr-origin-trace-propagation.md`](./lstr-origin-trace-propagation.md)
- [`lstr-pydantic-roundtrip-schema.md`](./lstr-pydantic-roundtrip-schema.md)
- [`message-tool-call-result-plane.md`](./message-tool-call-result-plane.md)
- [`migrations-three-case-bootstrap.md`](./migrations-three-case-bootstrap.md)
- [`openai-stream-default-and-retraction.md`](./openai-stream-default-and-retraction.md)
- [`provider-call-lifecycle-validation.md`](./provider-call-lifecycle-validation.md)
- [`provider-registry-configurator.md`](./provider-registry-configurator.md)
- [`should-import-boundary.md`](./should-import-boundary.md)
- [`sqlstore-idempotent-writes.md`](./sqlstore-idempotent-writes.md)
- [`state-cache-key.md`](./state-cache-key.md)
- [`studio-db-watcher.md`](./studio-db-watcher.md)
- [`tool-decorator-params-model.md`](./tool-decorator-params-model.md)
- [`tool-result-content-block-envelope.md`](./tool-result-content-block-envelope.md)
- [`track-invocation-stack.md`](./track-invocation-stack.md)
- [`verbosity-renderer-and-phone-home.md`](./verbosity-renderer-and-phone-home.md)

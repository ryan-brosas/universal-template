<!-- capsule-v2 -->
# Python skeleton-generator cache ladder — how does a stub generator decide reuse vs regenerate vs give-up without ever trusting a stale or poisoned skeleton?

**Source:** JetBrains DataSpell installed build `DS-261.26222.84`, `plugins/python-ce/helpers/generator3` plane. Codebase Memory `jetbrains-dataspell`. **Question:** When regenerating Python skeletons for an SDK, what state machine decides whether a module's skeletons are up-to-date, copyable from cache, failing, or outdated — and where do failure markers live so a crash can't masquerade as success?

## Two-tier content-addressed cache + tri-state status ladder
**Path/Symbol:** `plugins/python-ce/helpers/generator3/core.py` — `module_hash` (:149-158), `build_cache_dir_path` (:145-146), `skeleton_status` (:197-244), `SkeletonGenerator.reuse_or_generate_skeleton` (:540-582), `generate_skeleton` (:608-657), `redo_module` (:660-680); grammar in `constants.py` (:699-710).
**Signature:** `module_hash(mod_qname, mod_path)`; `skeleton_status(base_dir, mod_qname, mod_path, sdk_skeleton_state=None) -> SkeletonStatusId`; `reuse_or_generate_skeleton(mod_name, mod_path, mod_state_json) -> GenerationStatusId`.
**Data Shape:** per-SDK output dir (`self.output_dir`) holds live skeletons; shared cache dir holds `<cache>/<sha256>` subdirs keyed by sha256 of the module FILE bytes (`physical_module_hash`) or sha256(`sys.version`) for builtins; test mode truncates the hash to 10 chars. Skeleton identity is read back from a header comment `# by generator <maj.min>`. Failure is encoded two ways: `.failed__<qname>` stamp files (cache) and a legacy `<sdk-skeletons>/.blacklist` file with `path = version mtime-ms` lines (Java side stores milliseconds; Python divides by 1000). Per-module minimum versions come from `required_gen_version` (`name version` lines; `(default)` and `(built-in)` are special names).

### Decisive source
```python
def skeleton_status(base_dir, mod_qname, mod_path, sdk_skeleton_state=None):
    …
    if 'gen_version' not in skeleton_meta:
        failed_version = read_failed_version_from_stamp(base_dir, mod_qname)
        if failed_version:
            used_version = failed_version
            skeleton_meta['status'] = GenerationStatus.FAILED
        blacklist_record = read_failed_version_and_mtime_from_legacy_blacklist(base_dir, mod_path)
        if blacklist_record:
            …skeleton_meta['status'] = GenerationStatus.FAILED
        existing_skeleton_version = read_used_generator_version_from_skeleton_header(base_dir, mod_qname)
        if existing_skeleton_version:
            skeleton_meta['status'] = GenerationStatus.GENERATED
            used_version = existing_skeleton_version
    # remote skeletons have neither cache nor physical dir -> rely on binary mtime
    if mod_path and used_bin_mtime is not None and used_bin_mtime < file_modification_timestamp(mod_path):
        return SkeletonStatus.OUTDATED
    if skeleton_meta.get('status') == GenerationStatus.FAILED:
        return SkeletonStatus.OUTDATED if used_version < gen_version else SkeletonStatus.FAILING
    required_version = read_required_version(mod_qname)   # per-module override else (default)
    if required_version and used_version:
        return SkeletonStatus.OUTDATED if used_version < required_version else SkeletonStatus.UP_TO_DATE
    return SkeletonStatus.OUTDATED                        # missing or corrupted
```
And the crash-safe marker discipline inside generation itself:
```python
def generate_skeleton(name, mod_file_name, mod_cache_dir, output_dir):
    …
    create_failed_version_stamp(mod_cache_dir, name)   # stamped BEFORE import: a crash mid-import leaves FAILING, not "no data"
    action("importing")
    old_modules = list(sys.modules.keys())
    with imported_names_collected() as imported_module_names:
        __import__(name)
    redo_module(name, mod_file_name, mod_cache_dir, output_dir)  # deletes stamp after flush + incremental copy_skeletons
    # sweep sys.modules delta for synthetic submodules created by C libs (gtk._gtk style), skip
    # entries not requested via meta-path finder and lacking __file__
```

**Flow:** `reuse_or_generate_skeleton`: status(OUTDIR)==UP_TO_DATE → return UP_TO_DATE; ==FAILING → return FAILED; otherwise clear the remote `state.json` dict, compute cache dir by content hash, status(CACHE): OUTDATED → regenerate via `execute_in_subprocess_synchronously(name='Skeleton Generator Worker', func=generate_skeleton, …, failure_result=FAILED)` (import of arbitrary modules happens OFF the main process); FAILING → return FAILED; else `copy_skeletons(cache_dir → output_dir)` → COPIED. Status derivation order: fail-stamp/blacklist first, then skeleton header version, then mtime check, then FAILED-vs-version comparison, then required-version comparison.
**Invariant:** a missing/corrupt skeleton degrades to OUTDATED (retryable), never to "reuse"; FAILING is sticky only while `used_version >= gen_version` — bumping the generator version automatically re-arms failed modules; and the fail stamp exists BEFORE the dangerous import so a segfaulting C extension records why the cache entry is dead.
**Probe:** graph-live retrieval + coverage gate (all executed this pass):
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-dataspell", query: "generator3 skeleton cache required generation version outdated failing" }); // skeleton_status :197-244, reuse_or_generate_skeleton :540-582, generate_skeleton :608-657 rank hits
await mcp.codebase_memory.get_code_snippet({ project: "jetbrains-dataspell", qualified_name: "jetbrains-dataspell.plugins.python-ce.helpers.generator3.core.skeleton_status" }); // verbatim
await mcp.codebase_memory.check_index_coverage({ project: "jetbrains-dataspell", paths: ["plugins/python-ce/helpers/generator3/core.py"] }); // no_recorded_issue, metadata_match
```

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "jetbrains-dataspell", qualified_name: "jetbrains-dataspell.plugins.python-ce.helpers.generator3.core.SkeletonGenerator.reuse_or_generate_skeleton" });
await mcp.codebase_memory.get_code_snippet({ project: "jetbrains-dataspell", qualified_name: "jetbrains-dataspell.plugins.python-ce.helpers.generator3.core.build_cache_dir_path" }); // -> os.path.join(subdir, module_hash(...))
```

## Verdict
Adopt: content-hash-keyed two-tier skeleton cache; tri-state status resolved from explicit markers (stamp > blacklist > header version) with mtime only as the remote fallback; fail-before-import stamping; subprocess isolation for the import step; per-module `required_gen_version` overrides over a `(default)` floor. Adapt hash inputs and status vocabulary to your artifact type. Omit the legacy `.blacklist` path unless you must migrate pre-cache layouts, and the py2-era `version.txt`/pyparsing_py2 shims.

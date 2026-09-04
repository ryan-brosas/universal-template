<!-- capsule-v2 -->
# Resource attribute precedence — in what order do defaults, env vars, detectors, and explicit args merge?

**Source:** logfire MIT `main@e484a6b5`; Codebase Memory `ext-logfire`. **Question:** When service.name comes from configure(), OTEL_RESOURCE_ATTRIBUTES, a detector, and the fallback simultaneously, which wins and where is the conflict surfaced?

## LogfireConfig._build_resource
**Path/Symbol:** `logfire/_internal/config.py:_build_resource` (`config.py:1147-1232`).
**Signature:** `_build_resource(self) -> Resource`; merges via successive `.merge()` calls (later wins).
**Data Shape:** five precedence tiers; dedicated args warn on conflicting `resource_attributes` keys.

### Decisive source
```python
fallback_resource_attributes = {
    **common_resource_attributes(),          # process.runtime.*, host.*, os.* — always non-empty
    'service.instance.id': uuid4().hex,      # random unless detector/env sets one
}
if self.service_version is None:
    try: git_hash = get_git_revision_hash()
    except Exception: pass                   # git may be unavailable — ignore
    else:
        self.service_version = git_hash      # reflected in config span + inherited by children
        fallback_resource_attributes['service.version'] = git_hash
resource = Resource(fallback_resource_attributes).merge(Resource.create({}))  # + OTEL_RESOURCE_ATTRIBUTES + OTEL_EXPERIMENTAL_RESOURCE_DETECTORS
...
resource = resource.merge(get_aggregated_resources(detectors, Resource.get_empty()))
...
return resource.merge(Resource(otel_resource_attributes))   # resource_attributes arg + dedicated args ALWAYS win
```
Docstring enumerates the tiers explicitly: "(1) Low-precedence fallbacks … deliberately sit below the env vars so an explicit OTEL_RESOURCE_ATTRIBUTES still wins. (2) OTel default + env vars. (3) resource_detectors argument. (4) resource_attributes argument. (5) other configure() arguments." Conflict surfacing: for each dedicated key also present in `resource_attributes`, warn "the dedicated argument takes precedence" via `warn_at_user_stacklevel` (user-frame attribution).
Also here: `code_source` populates vcs.repository.* plus `logfire.code.work_dir = os.getcwd()` ONLY when both repo URL and revision are set; `process.pid` and `logfire.version` stamped unconditionally.
**Flow:** fallback → OTEL-defaults/env merge → explicit detectors merge → explicit attributes merge (final say) → fork-safety handled separately by `_register_at_fork_resource_updates` which patches pid AFTER fork by writing `provider._resource` directly ("before OpenTelemetry resets its locks… without acquiring inherited locks").
**Invariant:** The git-hash fallback writes BACK to `self.service_version` so executors serialization (`dataclasses.asdict` of `_LogfireConfigData`) carries it to child processes. Random `service.instance.id` must be uuid4-hex per-process, never persisted.
**Probe:** `tests/test_configure.py::test_service_version` family + test_resource_attribute_precedence — pins tier ordering.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-logfire", query: "_build_resource fallback_resource_attributes service.instance.id get_git_revision_hash", limit: 8, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the five-tier merge order and write-back-of-derived-version trick. Adapt attribute names to your semconv version. Omit at-fork patching if your runtime doesn't fork after configure.

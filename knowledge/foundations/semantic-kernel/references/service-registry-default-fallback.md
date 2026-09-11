<!-- capsule-v2 -->
# Service registry default fallback — how does a service_id resolve to one service, and what does "default" really mean?

**Source:** Microsoft semantic-kernel MIT `main@b39d95a34435f4c1d55dd00c86120ce118d847e1`; Codebase Memory `semantic-kernel`. **Question:** When code asks for a service by id and/or type, in what order are type and id applied, what does the magic id "default" do, and how do services get their identity?

## Type filter first, then id; "default" means "first of that type"
**Path/Symbol:** `python/semantic_kernel/services/kernel_services_extension.py:KernelServicesExtension.get_service` (68–109), `.get_services_by_type` (111–117), `.add_service` (129–139), `.remove_service` (141–145); identity contract `python/semantic_kernel/services/ai_service_client_base.py:AIServiceClientBase.model_post_init` (28–32).
**Signature:** `def get_service(self, service_id: str | None = None, type: type | tuple[type, ...] | None = None) -> AI_SERVICE_CLIENT_TYPE`.
**Data Shape:** `type` may be a class or a tuple (isinstance accepts both natively). The registry is a plain `MutableMapping[str, AIServiceClientBase]` keyed by service_id. `DEFAULT_SERVICE_NAME = "default"` (`const.py:6`).

### Decisive source
```python
services = self.get_services_by_type(type)          # 1. TYPE FILTER FIRST
if not services:
    raise KernelServiceNotFoundError(f"No services found of type {type}.")
if not service_id:
    service_id = DEFAULT_SERVICE_NAME               # 2. missing id -> "default"
if service_id not in services:
    if service_id == DEFAULT_SERVICE_NAME:
        return next(iter(services.values()))        # 3. "default" = FIRST of that type
    raise KernelServiceNotFoundError(
        f"Service with service_id '{service_id}' does not exist or has a different type.")
return services[service_id]

# identity: ai_model_id required (strip_whitespace, min_length=1); empty service_id backfilled
def model_post_init(self, __context):
    if not self.service_id:
        self.service_id = self.ai_model_id
```

**Flow:** filter the whole registry by isinstance against the requested type(s); if nothing matches that type, fail immediately with a type-shaped message; otherwise resolve the id — an absent/empty id becomes "default", and a missing "default" key falls back to the first registered service of that type (dict order); any other missing id is fatal. Registration normalizes input at construction: the `rewrite_services` field_validator (37–49) accepts a single service, a list, or a dict and keys everything by `service_id or DEFAULT_SERVICE_NAME`. `add_service(overwrite=False)` raises `KernelFunctionAlreadyExistsError` on duplicates — note the FUNCTION exception class is reused for services.
**Invariant:** type filtering happens BEFORE id lookup, so a wrong-type request can never be rescued by a matching id; "default" never means "a specific registered id" — it means "any first match", which is why registering a service literally named "default" shadows the fallback for its type only. A kernel holding live provider clients cannot be `model_dump`ed or deep-copied (TypeError — the HTTP client is not serializable).
**Probe:** `python/tests/unit/kernel/test_kernel.py::test_get_default_service_by_type` (1069–1072: "default" id resolves via get_services_by_type), `::test_get_service_no_id` (1105–1108: no id → first service), `::test_get_service_with_multiple_types_union` (1094–1099: tuple AND PEP-604 Union both work as isinstance targets), `::test_kernel_add_service_twice` (1016–1020: duplicate → KernelFunctionAlreadyExistsError), `::test_kernel_model_dump_fail_with_services` (1166–1173: TypeError with live OpenAI service); `python/tests/unit/services/test_ai_service_client_base.py::test_init_no_service_id` (service_id backfilled from ai_model_id).
**Coverage caveat:** Codebase Memory MCP not connected this session; whole-file direct reads used instead of graph snippets (recorded in verification.md).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "semantic-kernel", query: "get_service get_services_by_type DEFAULT_SERVICE_NAME add_service rewrite_services", limit: 10, fields: ["signature", "name", "file"] });
```
(Not executable this pass — MCP surface absent; recorded as degraded retrieval, command kept byte-for-byte for the next connected pass.)

## Verdict
Adopt the two-stage resolution (type gate, then id with default-as-first-match) and the construction-time normalization of single/list/dict registries — they make "which service" a pure function of (registry, type, id). Adapt the exception choice: SK reusing KernelFunctionAlreadyExistsError for services is a historical wart, not a pattern to copy. Omit the serialization assumption: keep live clients out of any dump/copy path or mirror SK's hard TypeError instead of silently dropping them.

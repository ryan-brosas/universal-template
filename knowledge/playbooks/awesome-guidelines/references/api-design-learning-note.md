# API design — learning note

**Status:** deep ingest (2026-08-28). **Feeds:** `api-design-*.md` capsules, `api-design-practices` application skill.

## Sources read

| Source | What we extracted |
|---|---|
| [Microsoft Azure REST API Guidelines](https://github.com/microsoft/api-guidelines/blob/vNext/azure/Guidelines.md) (2025) | URL shape, idempotency (all methods including POST), error contract (`x-ms-error-code`), JSON camelCase, pagination (`nextLink`, `value`), `api-version` query param, LRO patterns, extensible enums |
| [Google AIP-121 Resource-oriented design](https://google.aip.dev/121) | Resources as nouns, standard methods (Get/List/Create/Update/Delete), strong consistency after mutations, acyclic references, stateless protocol |
| [Google AIP-122 Resource names](https://google.aip.dev/122) | Hierarchical names (`publishers/123/books/les-miserables`), plural collections, `name`/`parent` fields, no embedding resources |
| [Google AIP-132 List](https://google.aip.dev/132) | GET list, `parent`, pagination fields required from day one |
| [Google AIP-158 Pagination](https://google.aip.dev/158) | `page_size`/`page_token`/`next_page_token`, opaque tokens, adding pagination later is breaking |
| [Google AIP-193 Errors](https://google.aip.dev/193) | `google.rpc.Status`, required `ErrorInfo` (reason+domain+metadata), PERMISSION_DENIED before NOT_FOUND, HTTP JSON mapping |
| awesome-guidelines index | Also lists [JSON API recommendations](http://jsonapi.org/recommendations), [Microsoft api-guidelines repo](https://github.com/Microsoft/api-guidelines), [Google Cloud API Design Guide](https://cloud.google.com/apis/design) — AIPs are the live Google corpus |

## Mental model

Two converging schools:

1. **Resource-oriented (Google AIP)** — Collections and resources with hierarchical **names** (not primary keys in URLs alone); small verb set; List/Get mandatory; pagination and errors designed for SDK generation; API surface ≠ database schema.
2. **HTTP contract (Azure)** — Explicit **api-version** on every call; **idempotent everything** (POST via repeatability headers); stable **machine-readable error codes** (`x-ms-error-code` = body `error.code`); camelCase JSON; **nextLink** pagination with absolute URLs.

Porting rule: pick one primary style per API and cross-check the other for gaps (errors, pagination opacity, permission vs not-found ordering).

## Decision tables

### Resource naming (Google)

| Element | Rule |
|---|---|
| Collection segment | plural camelCase: `publishers`, `books` |
| Resource ID | user-set: lowercase RFC-1034-ish; service-set: document max length |
| Resource message | first field `string name` = full relative name |
| List/create request | `parent` = collection name |
| References | string resource name + `resource_reference`; never embed full resource messages |
| Graph | parent-child acyclic; references acyclic (or use output-only fields) |

### HTTP methods & idempotency (Azure + Google)

| Operation | Preferred | Success codes | Notes |
|---|---|---|---|
| Read one | GET | 200 | Cacheable |
| Read collection | GET | 200 | Must paginate from v1 |
| Create | PUT/PATCH (Azure SHOULD) or POST | 201 | POST must return resource URL; must be idempotent |
| Replace | PUT | 200/201 | Whole resource |
| Partial update | PATCH | 200 | JSON Merge Patch (Azure) |
| Delete | DELETE | 204/202 | Async → 202 + LRO |
| Action | POST `:action` (Google custom) | varies | Prefer standard methods first |

**Azure invariant:** all methods idempotent — POST uses `Repeatability-Request-ID` + `Repeatability-First-Sent` when needed.

### Errors

| Concern | Azure | Google AIP-193 |
|---|---|---|
| Machine id | `x-ms-error-code` header = `error.code` (contract!) | `ErrorInfo.reason` + `ErrorInfo.domain` |
| Human text | `error.message` (not stable contract except debug) | `Status.message` + optional `LocalizedMessage` |
| Auth vs missing | (document per op) | Check permission **before** existence → 403 vs 404 |
| Client parsing | Compare `code` strings | Read `ErrorInfo.metadata`, not message regex |
| Partial failures | Avoid; use LRO metadata if bulk | Avoid; use LRO |

### Pagination

| | Azure list | Google List |
|---|---|---|
| Request | `maxpagesize`, `skip`, `top`, optional OData-style `filter`/`orderby` | `page_size`, `page_token` |
| Response | `value[]`, `nextLink` absolute URL (omit on last page) | `resources[]`, `next_page_token` (empty = end) |
| Token | Opaque URL in `nextLink` includes `api-version` | Opaque, not user-parseable |
| Breaking change | N/A | **Cannot add pagination later** — ship day one |

### Versioning (Azure)

- Required query `api-version=YYYY-MM-DD` (-preview suffix for preview).
- Missing → 400 `MissingApiVersionParameter`; unknown → 400 `UnsupportedApiVersionValue`.
- **No** version segment in URL path.
- Preview → GA must use **later date**; no breaking changes without deprecation headers (`azure-deprecating`).

## Anti-patterns

| Pattern | Why |
|---|---|
| API mirrors DB tables 1:1 | Leaks storage; blocks evolution (AIP-121) |
| Parse error `message` strings | Breaks when wording changes (AIP-193, Azure) |
| Unpaginated list RPC | Adding pagination later breaks clients (AIP-158) |
| 404 before auth check on secret resource | Leaks existence (AIP-193) |
| Version in URL path + query | Azure forbids path version segment |
| `nextLink: null` | Azure: omit field entirely on last page |
| UUIDs in user-visible URLs when readable IDs work | Azure SHOULD keep URLs readable |

## Reconciliation notes (catalog)

- **JSON field naming:** Azure camelCase; catalog TS may use project eslint — document in OpenAPI.
- **Conventional errors in internal APIs:** map domain errors to stable `code` / `ErrorInfo.reason` at boundary.
- **Breaking change policy:** pair with `semver-learning-note.md` for package APIs; HTTP APIs use `api-version` dates.

## Skill trace

- Capsules: `api-design-resource-names.md`, `api-design-http-idempotency.md`, `api-design-errors-machine-readable.md`, `api-design-pagination-and-lists.md`, `api-design-versioning-contract.md`
- Application: `api-design-practices/SKILL.md`
- Router: `awesome-guidelines`, `coding-best-practices` topic index

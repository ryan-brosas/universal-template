<!-- capsule-v2 -->
# Resource names — how should clients address a resource without knowing your schema?

**Source:** Google AIP-121/122; Azure URL collection segments. **Question:** What string do clients store as the canonical resource identifier?

## Name hierarchy seam
**Path/Symbol:** RPC/REST resource model (e.g. `publishers/{publisher}/books/{book}`).
**Signature:** `string name` on resource messages; `string parent` on List/Create requests.
**Data Shape:** slash-separated segments; plural collection ids; singular resource ids.

### Decisive pattern
```text
publishers/123/books/les-miserables   # relative resource name (AIP-122)
GET /v1/publishers/123/books/les-miserables   # HTTP binding adds version prefix
```

**Flow:** define resource type + collection plural → assign stable `name` → reference other resources by **name string** (not embedded messages) → List uses `parent` pointing at collection.
**Invariant:** API resource graph is a **DAG** — acyclic parent-child and reference edges (AIP-121); duplicate collection segment in one name is invalid (`people/x/people/y`).
**Probe:** OpenAPI/`google.api.resource` patterns match runtime; Get succeeds after Create with same `name`; no tuple/self-link alternate IDs in public API.

## Verdict
Adopt hierarchical names with plural collections; adapt HTTP prefix (`/v1/`) vs Azure tenant URL pattern; omit embedding resource protos inside resources (AIP-122). Learning note: `api-design-learning-note.md`.

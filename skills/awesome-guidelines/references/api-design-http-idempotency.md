<!-- capsule-v2 -->
# HTTP idempotency — how do retries avoid double-create?

**Source:** Azure REST Guidelines (Request/Response); Google standard methods. **Question:** What happens if the client sends the same write twice after a timeout?

## Idempotency seam
**Path/Symbol:** HTTP method handlers for PUT/PATCH/POST/DELETE.
**Signature:** safe retry without duplicate side effects ("exactly once" semantics from client view).
**Data Shape:** optional `Repeatability-Request-ID` + `Repeatability-First-Sent` headers (Azure POST).

### Status code matrix (sync success — Azure)
| Method | Role | Codes |
|---|---|---|
| GET/HEAD | read | 200 |
| PUT | create/replace whole | 200, 201 |
| PATCH | merge patch | 200, 201 |
| POST | create (if used) | 201 + **Location/body URL** |
| DELETE | remove | 204 |

**Flow:** prefer PUT/PATCH for create (named, idempotent) → if POST create, return 201 with resource URL → make POST idempotent via repeatability headers or same-body window → async completion returns **202** + operation monitor (LRO).
**Invariant:** **All** Azure HTTP operations must be idempotent — cloud clients **will** retry on no response (Azure Introduction).
**Probe:** duplicate identical PUT with same keys returns same resource state/etag; duplicate POST with same repeatability id returns same 201 response; integration test replays after simulated timeout.

## Verdict
Adopt idempotent writes + explicit 201/202 semantics; adapt POST repeatability mechanism to your stack; omit non-idempotent POST without documented retry contract. Learning note: `api-design-learning-note.md`.

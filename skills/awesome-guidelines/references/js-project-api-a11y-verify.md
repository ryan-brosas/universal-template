<!-- capsule-v2 -->
# API, accessibility, and verify — do REST, security, a11y tooling, and project checks align with guidelines?

**Source:** project-guidelines §9 API, §10 Accessibility. **Question:** Are public APIs consistent and is accessibility wired from project start?

## API design seam
**Path/Symbol:** REST HTTP API surface, JSON payloads.
**Signature:** kebab-case plural URLs; camelCase JSON; structured errors.
**Data Shape:** GET /v1/users/123; Bearer auth header.

### Decisive pattern
```http
GET /v1/schools/2/students/31
Authorization: Bearer …
```
```json
{ "code": 1234, "message": "Validation Failed", "errors": [{ "field": "email", "message": "Invalid email" }] }
```

**Flow:** **resource-oriented** URLs — **kebab-case plural** nouns (`/users`) — **camelCase** query/body fields; collections → **`usersList`** in code → **HTTP verbs** for CRUD; nest relations `/schools/2/students/31` → **`/v1`** prefix leftmost → errors: **`code`, `message`, `description`**; auth errors **generic** → status codes: **200/201/204/400/401/403/404/500** subset → **limit/offset** pagination; optional **`fields`** sparse responses → document endpoints in README; **Swagger/ApiBlueprint** optional.
**Invariant:** verb paths (`/createUser`), table names in URLs, or tokens in query string fail API review.
**Probe:** route inventory; OpenAPI/README API section; error shape spot check.

## API security seam
**Flow:** **HTTPS only** — reject plain HTTP (**403**) → tokens in **`Authorization: Bearer`** never URL query → short-lived auth codes → **rate limiting** → **helmet** headers → validate **Content-Type** (prefer `application/json`) → canonicalize/reject bad input **400** → safe **JSON serialization** (no arbitrary JS) → cross-check **API Security Checklist**.
**Invariant:** basic auth over HTTP or token in query fails security review.
**Probe:** curl http:// → 403; grep `token=` in route handlers.

## Accessibility seam
**Flow:** from **project start**: schedule **lighthouse/axe** audits; agree minimum score → add framework **a11y eslint plugin** (jsx-a11y etc.) → optional **axe-core** in tests/Storybook → prefer accessible component libraries when applicable → basics: **alt**, **heading order**, **contrast**, **link names**, semantic **lists** → deep conformance: **`wcag-accessibility-practices`**.
**Invariant:** zero a11y lint/automation on UI-heavy greenfield JS project fails a11y setup review.
**Probe:** lighthouse CI artifact; eslint jsx-a11y enabled; manual tab order note.

## Verify seam
**Flow:** new JS project checklist — git/docs + env/lockfile/tests + structure/lint + API/a11y docs → run **`npm test`**, **`npm run lint`**, **audit**, optional **axe/lighthouse** on key routes before merge.
**Probe:** CI pipeline includes lint+test+audit; README complete per sample template.

## Verdict
Consistent REST JSON API, transport security, early a11y automation, full project verify stack. Learning note: `js-project-learning-note.md`.

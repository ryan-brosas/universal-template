<!-- capsule-v2 -->
# API versioning — how do callers pin contract without path churn?

**Source:** Azure API Versioning section. **Question:** How does a client request a specific contract generation?

## api-version seam
**Signature:** required query parameter on **every** operation (including `nextLink` and LRO poll URLs).
**Data Shape:** `api-version=YYYY-MM-DD` or `YYYY-MM-DD-preview`.

```text
PUT https://service.azure.com/users/Jeff?api-version=2021-06-04
```

**Flow:** client sends `api-version` → missing → 400 `MissingApiVersionParameter` → unknown → 400 `UnsupportedApiVersionValue` listing supported stables + latest preview → preview graduates to GA with **later date** (never reuse preview date).
**Invariant:** **no** `/v1/` version segment in path when using query `api-version` (Azure DO NOT); breaking changes require new version date + deprecation communication (`azure-deprecating` header for human ops).
**Probe:** integration tests without `api-version` fail 400 with documented code; GA release date > preview date; OpenAPI documents enum of supported versions.

## Verdict
Adopt explicit date-based query versioning for public HTTP APIs; adapt to header-based version schemes only with same immutability rules; omit silent breaking changes within a version. Learning note: `api-design-learning-note.md`. Pair package semver with `semver-learning-note.md` for libraries.

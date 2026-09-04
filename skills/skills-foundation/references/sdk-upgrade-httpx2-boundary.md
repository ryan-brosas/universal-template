<!-- capsule-v2 -->
# Anthropic SDK 0.x → 1.x Upgrade — the httpx→httpx2 boundary and mechanical inventory ladder

**Source:** anthropics/skills (Apache-2.0 example) `main@3b3fad9`; Codebase Memory `skills`. **Question:** What is the complete contract for upgrading a project's `anthropic` Python SDK dependency from 0.x to 1.x, and which invariant a porter would get wrong?

## Signal-driven inventory → boundary-corrected httpx2 migration
**Path/Symbol:** `skills/claude-api/python/claude-api/sdk-upgrade.md` (286L, read whole) — Step 0 scope/versions (:1–41), Step 1 inventory table (:42–79), Step 3 httpx→httpx2 (:80–111), Steps 4–10 (:113–257), Step 11 verify (:259–263), Step 12 report (:265–272).
**Signature:** SKILL.md subcommand contract: `/claude-api upgrade [python] [src/]` — reads `sdk-upgrade.md` and executes in order, never summarizes.
**Data Shape:** `anthropic` 1.x = small step from last 0.x: removed long-deprecated surface, HTTP layer moved from `httpx` to its maintained fork `httpx2`, min Python 3.10. `httpx2` is API-compatible (same classes/behavior), version line 2.x, published by Pydantic. `httpx2.alias_httpx()` makes `import httpx`/`import httpcore` resolve to httpx2/httpcore2 process-wide.

### Decisive source
```python
# Before
import httpx
from anthropic import Anthropic, DefaultHttpxClient
client = Anthropic(
    timeout=httpx.Timeout(60.0, connect=5.0),
    http_client=DefaultHttpxClient(proxy="http://proxy.example", transport=httpx.HTTPTransport(retries=1)),
)
# After
import httpx2 as httpx
```
```python
# application entry point — must run before anything imports httpx/httpcore
import httpx2
httpx2.alias_httpx()
import httpx  # now the httpx2 module: httpx.Client is httpx2.Client
```

**Flow:** Step 0 (confirm scope; establish current+target versions — a published 1.x must exist before writing any pin; `pip index versions anthropic`; if no 1.x release, STOP) → Step 1 (signal-driven inventory via `rg -n -F` for each table row, classify each hit: SDK call site / unrelated use / test / docs) → Steps 2–10 (per-section mechanical edits) → Step 11 verify (re-run greps, `compileall`, type checker, tests) → Step 12 report (lead with outcome; list user-owned decisions).
**Invariant:** the httpx→httpx2 change matters ONLY where `httpx` objects cross the SDK boundary — objects passed in (`httpx.Timeout`, `httpx.Limits`, transports, whole `httpx.Client`/`AsyncClient` as `http_client=`) and objects coming out (`APIStatusError.response`, `.http_response`, `cast_to=httpx.Response`) must be `httpx2`. An old-`httpx` client passed as `http_client=` raises `TypeError` at construction. Plain values (`timeout=30.0`, `max_retries=3`) need nothing. Instrumentation/mocking that patches `httpx` (OpenTelemetry `HTTPXClientInstrumentor`, Sentry, `respx`, `pytest-httpx`, `vcrpy`) keeps importing fine but silently stops seeing SDK traffic — fix with `httpx2.alias_httpx()` (alias) run before them, NOT by swapping in an unverified `*-httpx2` instrumentation package. `alias_httpx()` is for applications only, never for a library's import path.
**Probe:** No upstream test runner (docs-only). Deterministic: `grep -c 'httpx2' skills/claude-api/python/claude-api/sdk-upgrade.md` = 22; `grep -c 'alias_httpx' skills/claude-api/python/claude-api/sdk-upgrade.md` = 8; `grep -c 'BREAKS' skills/claude-api/python/claude-api/sdk-upgrade.md` = 22; `grep -c 'DECIDE' skills/claude-api/python/claude-api/sdk-upgrade.md` = 13.

## Get live surrounding code
**Retrieve:**
**Retrieve:** doc-shaped/BM25-gap note — `search_graph` text queries return ZERO on this graph (Section nodes carry no searchable tokens); use `search_code`, executed live:
```bash
codebase-memory-mcp cli search_code '{"project": "skills", "pattern": "alias_httpx", "limit": 10}'
# resolves `skills/claude-api/python/claude-api/sdk-upgrade.md` line-exact (verified 2026-08-24)
```

## Verdict
Adopt the signal-driven-inventory + boundary-corrected httpx2 migration + user-owned-decision-separation contract for any SDK major-version upgrade guide. Adapt the specific removed/renamed names to the target SDK. Omit the Anthropic-specific model names and the `migrate`/`prompt-audit` cross-references (covered by other claude-api capsules). Coverage caveat: no executable test — contract pinned by source grep + graph metadata_match only.

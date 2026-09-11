<!-- capsule-v2 -->
# Ephemeral-SQLite Production Warning — how do you warn about data loss you cannot detect?

**Source:** awaithumans Apache-2.0 `main@bc05b8e7`; Codebase Memory `mnt-hdd-utopia-inspo-awaithumans`. **Question:** When container runtimes silently wipe your DB volume, what guardrail works without runtime-specific filesystem heuristics that age badly?

## Operator-acknowledgment durability guardrail
**Path/Symbol:** `packages/python/awaithumans/server/app.py:_warn_if_ephemeral_sqlite_in_production` (:229–297); direct tests `packages/python/tests/server/test_ephemeral_sqlite_warning.py`.
**Signature:** `_warn_if_ephemeral_sqlite_in_production() -> None` (sync, called during startup/lifespan).
**Data Shape:** Reads `settings.is_production`, `settings.DATABASE_URL` (None ⇒ SQLite default), `settings.ALLOW_EPHEMERAL_DB`. Emits either nothing, one INFO audit record, or ONE multi-line WARNING banner naming DB_PATH, DATABASE_URL, and the three remediation env vars.

### Decisive source
```python
if not settings.is_production:
    return                       # dev boots on SQLite BY DESIGN — stay quiet
using_sqlite = not settings.DATABASE_URL or settings.DATABASE_URL.startswith(
    ("sqlite://", "sqlite+aiosqlite://")
)                                # scheme decides, not just the unset default
if not using_sqlite:
    return
if settings.ALLOW_EPHEMERAL_DB:
    logger.info("AWAITHUMANS_ALLOW_EPHEMERAL_DB=true — skipping the "
                "production-SQLite durability warning (operator-acknowledged).")
    return                       # acknowledged risk STILL leaves an audit trail
# ...72-char divider banner: headline + resolved DB_PATH + both fixes
#    + the ack var...
logger.warning("\n".join(banner_lines))   # ONE record, not 20 lines
```

**Flow:** production? → sqlite scheme or default? → operator acked? → INFO note and stop : emit single multi-line WARNING whose body carries the resolved `DB_PATH`, the Postgres fix (`AWAITHUMANS_DATABASE_URL`), the durable-volume fix (`AWAITHUMANS_DB_PATH` on a mounted volume), and the silencing ack (`AWAITHUMANS_ALLOW_EPHEMERAL_DB=true`).
**Invariant:** "ephemeral" is never detected by probing the filesystem — the env var is the operator's signed acknowledgment because runtime heuristics (overlayfs detection et al.) age badly. The banner ships as ONE log record so level-based aggregation surfaces one event; tests pin exact substrings (headline marker + every env-var name + resolved DB_PATH) so a cleanup can't truncate it into a skimmable one-liner.
**Probe:** `tests/server/test_ephemeral_sqlite_warning.py` (:51–86 one-WARNING + substring pins; :89–111 explicit sqlite+aiosqlite URL also warns; :114–130 Postgres silent; :133–149 dev silent). Deterministic source probe (runner-blocked run): `grep -c 'ALLOW_EPHEMERAL_DB' packages/python/awaithumans/server/app.py` → ≥3 occurrences (ack read, INFO text, banner text).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-awaithumans", query: "warn ephemeral sqlite production warning lifespan", limit: 6, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the acknowledgment-over-heuristics posture, the scheme-or-default SQLite detection, and the one-record multi-line banner with pinned actionable strings. Adapt which settings names/env prefix carry the ack. Omit filesystem-detection attempts entirely — that is the failure mode this design exists to avoid.

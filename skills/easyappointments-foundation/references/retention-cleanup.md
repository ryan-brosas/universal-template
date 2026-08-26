<!-- capsule-v2 -->
# Retention-based customer data cleanup — how do you purge stale customer records without touching anyone with live or future appointments?

**Source:** easy!Appointments GPL-3.0 `main@359c3649dc1977fa3fe882b422a462d77c8abce4`; Codebase Memory `ext-easyappointments`. **Question:** What is the exact retention predicate, and how do storage files and DB rows age out together?

## Cleanup library
**Path/Symbol:** `application/libraries/Cleanup.php:43` (`run`, 43–49), `:54` (`cleanup_sessions`, 54–76), `:139` (`cleanup_customer_data`, 139–178). Invoked from `application/controllers/Console.php:172` (CLI console command).
**Signature:** `cleanup_customer_data(): void`
**Data Shape:** `STORAGE_RETENTION_DAYS = 90` (`constants.php:157`) governs file GC; setting `data_retention_days` (int, **0 disables**) governs DB GC. Session files match glob `ea_session*`; logs `log-*.php`.

### Decisive source
```sql
-- application/libraries/Cleanup.php:152-162 — the purge predicate
SELECT DISTINCT c.id, c.email
FROM users c
INNER JOIN roles r ON r.id = c.id_roles AND r.slug = 'customer'
WHERE c.id NOT IN (
    SELECT DISTINCT id_users_customer FROM appointments WHERE end_datetime >= ?
)
AND c.create_datetime < ?
```

**Flow:** `run()` executes sessions → logs → cache → customers in order; file tiers delete by `filemtime < time - 90d` preserving `index.html/.gitkeep/.htaccess`; the customer tier computes cutoff once, selects role-customer ids with NO appointment ending after cutoff AND created before cutoff, then deletes one-by-one through `customers_model->delete` with per-row try/catch so a single failure doesn't abort the sweep.
**Invariant:** the two conditions are asymmetric on purpose — "no FUTURE-or-live appointments" (`end_datetime >= now-cutoff`) protects anyone still booking, while "created before cutoff" gives brand-new dormant customers their full retention window before eligibility. Deletion goes through the model (cascading settings/user_settings), never raw SQL DELETE. Porters who use `create_datetime >=` or drop the role join would wipe admins/providers or newborn accounts.
**Probe:** `grep -c "end_datetime >= ?" application/libraries/Cleanup.php` (= 1).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-easyappointments", query: "cleanup_customer_data", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt the dual-predicate purge + per-row failure isolation + preserve-list for cache GC; adapt the raw SQL to your ORM but keep it a single set-based select; omit nothing else. Direct tests: none upstream.

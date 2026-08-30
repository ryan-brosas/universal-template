<!-- capsule-v2 -->
# Appointment-relationship customer access — how do you scope customer-record visibility to appointment history?

**Source:** easy!Appointments GPL-3.0 `main@359c3649dc1977fa3fe882b422a462d77c8abce4`; Codebase Memory `ext-easyappointments`. **Question:** How does `limit_customer_access` turn "customer rows" into per-provider/per-secretary relationship-scoped reads?

## Permissions::has_customer_access
**Path/Symbol:** `application/libraries/Permissions.php:55` (`has_customer_access`, lines 55–95).
**Signature:** `has_customer_access(int $user_id, int $customer_id): bool`
**Data Shape:** Setting `limit_customer_access` (truthy = restricted mode). Role slugs: `admin|provider|secretary|customer` (`application/config/constants.php:47-50`). Secretary→providers is an array on the secretary row.

### Decisive source
```php
// application/libraries/Permissions.php:63-92 — admin bypass, provider own-history, secretary delegated fan-out
if ($role_slug === DB_SLUG_ADMIN || !$limit_customer_access) { return true; }
if ($role_slug === DB_SLUG_PROVIDER) {
    return $this->CI->appointments_model->query()
        ->where(['id_users_provider' => $user_id, 'id_users_customer' => $customer_id])
        ->get()->num_rows() > 0;
}
if ($role_slug === DB_SLUG_SECRETARY) {
    $secretary = $this->CI->secretaries_model->find($user_id);
    foreach ($secretary['providers'] as $secretary_provider_id) {
        $has_appointments_with_customer = $this->CI->appointments_model->query()
            ->where(['id_users_provider' => $secretary_provider_id, 'id_users_customer' => $customer_id])
            ->get()->num_rows() > 0;
        if ($has_appointments_with_customer) { return true; }
    }
    return false;
}
return false; // customers and unknown roles: never
```

**Flow:** role lookup via users→roles value chain → admin or disabled-setting short-circuit → provider checks OWN appointment history with the customer → secretary checks EACH managed provider's history → default deny.
**Invariant:** access derives from **appointment relationships, not ownership columns** — a provider who never had an appointment with the customer cannot read them even in the same tenant. Secretaries inherit through their managed providers only (one hop, no transitive closure). Default posture is deny for every other role including `customer`. Porters who key this off a workspace/tenant column lose the whole point of the setting.
**Probe:** `grep -c "id_users_provider.*id_users_customer\|id_users_provider' => \$secretary_provider_id" application/libraries/Permissions.php` (= 2 where-clauses).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-easyappointments", query: "has_customer_access", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt relationship-derived access + one-hop secretary delegation + explicit deny default; adapt the num_rows probes to EXISTS queries; omit nothing — this is the repo's multi-tenant-auth core. Direct tests: none upstream.

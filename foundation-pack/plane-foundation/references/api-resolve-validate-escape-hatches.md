<!-- capsule-v2 -->
# Resolve-and-validate with operator escape hatches — how do trusted internal hosts coexist with a hard SSRF block?

**Source:** Plane AGPL-3.0-only `preview@e056bbf9eb6b511cdc0a5823b1bd6922e561a485`; Codebase Memory `plane`. **Question:** when an operator must reach a private internal service by DNS name, how do you relax the block WITHOUT reopening rebinding or wildcard trust?

## resolve_and_validate + validate_url
**Path/Symbol:** `apps/api/plane/utils/ip_address.py`:`resolve_and_validate` (:105–156), `validate_url` (:159–196); host-match arm in `url_security.py::_fetch_validated_hop` (:172–180).
**Signature:** `resolve_and_validate(hostname, allowed_ips=None, require_safe=True) -> list[str]`; `validate_url(url, allowed_ips=None, allowed_hosts=None) -> None` (raises `ValueError`).
**Data Shape:** returns resolver-order de-duplicated IP strings to pin against; `allowed_ips` is a list of `ip_network`s; `allowed_hosts` is an iterable of exact hostname strings (case-insensitive, trailing dot stripped).

### Decisive source
```python
normalized_host = hostname.rstrip(".").lower()
trusted = bool(allowed_hosts) and normalized_host in {
    (h or "").rstrip(".").lower() for h in allowed_hosts if h
}
# Resolve once (and validate unless the host is operator-trusted), then pin
ips = resolve_and_validate(hostname, allowed_ips=allowed_ips, require_safe=not trusted)
```
and inside resolve_and_validate:
```python
if require_safe and not _is_allowed_ip(ip, allowed_ips) and is_blocked_ip(ip):
    raise ValueError("Access to private/internal networks is not allowed")
if ip_str not in validated:
    validated.append(ip_str)
```
`validate_url`'s own docstring: *"this validates at a point in time. To defeat DNS-rebinding (TOCTOU), the actual request must be pinned ... see plane.utils.url_security.pinned_fetch."*

**Flow:** normalize host → trusted-host check (exact match only; empty list trusts nothing) → resolve via getaddrinfo (gaierror AND IDNA UnicodeError both surface as `ValueError("Hostname could not be resolved")`) → reject if ANY resolved address is blocked unless covered by `allowed_ips`; trusted hosts skip the block check but resolution still runs so the caller can still pin.
**Invariant:** mixed public+private DNS answers fail closed (an attacker otherwise steers the connection to the private answer); trusted-host bypass never skips resolution or pinning — it only skips the classification.
**Probe:** `test_url_security.py::TestResolveAndValidate::test_raises_if_any_resolved_ip_is_private` (:107–114) and `TestPinnedFetch::test_allowed_host_skips_block_check_but_still_pins` (:210–232, asserts `require_safe=False` yet URL == IP literal, Host=silo). Allowlist semantics additionally pinned by `test_work_item_link_task.py::TestValidateUrlAllowlist` :108–148 (exact/case-insensitive match, empty list bypasses nothing, DNS still skipped only for trusted hosts).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "plane", query: "resolve and validate hostname allowed hosts trusted require safe", limit: 10, fields: ["signature", "name", "file"] });
```
Observed live at pass 2: ranks `resolve_and_validate` :105–156 #1.

## Verdict
Adopt the two-axis escape hatch (IP networks vs exact hostnames) and the trusted-hosts-still-pin rule; adapt the settings plumbing (`WEBHOOK_ALLOWED_IPS/HOSTS` env parsing) to your config layer; omit Plane's specific Silo/docker-service rationale.

<!-- capsule-v2 -->
# SSRF guard — how do you let users import remote images/URLs without exposing internal networks?

**Source:** FreeScout AGPL-3.0 `master@ab2772536811d5de6e23121c5d086aeb50f3db2c`; Codebase Memory `ext-freescout`. **Question:** What is the full defense chain — scheme, host canonicalization, IP-literal decoding, DNS resolution, redirect re-validation, and allowlist escape hatch — applied before fetching a user-supplied URL?

## Helper::checkUrlIpAndHost + sanitizeRemoteUrl
**Path/Symbol:** `app/Misc/Helper.php:2097-2187` (`checkUrlIpAndHost`), `:2063-2088` (`sanitizeRemoteUrl`), `:94-131` (`$restricted_ssrf_hosts`), `:2189+` (`isSafeHost`).
**Signature:** `checkUrlIpAndHost($url, $throw_exception = false): string` (returns '' when unsafe); `sanitizeRemoteUrl($url, $throw_exception = false, $follow_redirects = true)`.
**Data Shape:** blocklist = static array mixing exact IPs AND CIDR masks (`127.0.0.0/8`, `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `169.254.0.0/16`, `100.64.0.0/10` CGNAT, `fe80::/10`, `fc00::/7`, IPv4-mapped `::ffff:0:0/96`, AWS metadata `169.254.169.254` + `fd00:ec2::254`, benchmarking/multicast/reserved ranges) plus runtime self-references (`gethostname()`, its IP, own domain, `$_SERVER['SERVER_ADDR'/'LOCAL_ADDR']`). Allowlist via `APP_REMOTE_HOST_WHITE_LIST` env.

### Decisive source
```php
// app/Misc/Helper.php:2128-2152 — expand EVERY spelling of the host into candidates
$host = str_replace(['[', ']'], '', $host);
$hosts_to_check = [$host];
$host_hex_to_ip = self::hexToIp($host);              // 0x7f000001 / 2130706433 forms
if ($host_hex_to_ip && $host_hex_to_ip != $host) { $hosts_to_check[] = $host_hex_to_ip; }
if (!self::isValidIp($host)) {
    $remote_host_ip = gethostbyname($host);          // current A record
    ...
    $dns_records = dns_get_record($host, DNS_A | DNS_AAAA);  // ALL A + AAAA records
    foreach ($dns_records as $dns_record) { ... $hosts_to_check[] = ...; }
}
// :2160-2175 in isSafeHost — canonicality gate kills exotic encodings
if (substr($host, 0, 2) == '0x') { return false; }   // any hex-ish token rejected outright
if (self::isValidIp($host)) {
    if (inet_pton($host) === false) { return false; } // accepts ONLY standard text forms:
}   // 127.1, 2130706433, 0177.0.0.1 are NOT inet_pton-clean → rejected
```
Redirect arm (:2069-2085): loop up to **20** times — `curlGetNextRedirectedUrl` fetches with `CURLOPT_FOLLOWLOCATION=0` and parses the Location header manually; every new URL goes through `checkUrlIpAndHost` again before being followed.
**Flow:** normalize IPv6-in-URL → require scheme ∈ {http,https} (file:// dies here) → build candidate host set (literal, hex-decoded, A, AAAA) → each candidate must pass `isSafeHost`: allowlist wins first, then blocklist exact-or-CIDR, then encoding traps. Callers: a custom validator for all remote-URL form fields (AppServiceProvider.php:35-53) and `Customer::setPhotoFromRemoteFile` (Customer.php:1506-1517, EXCEPTION_UNSAFE_URL code distinguishes "blocked" from "network error").
**Invariant:** validation happens BEFORE every network step INCLUDING each redirect hop (TOCTOU note: the final fetch itself uses `CURLOPT_REDIR_PROTOCOLS` http/https-only but does not re-resolve DNS — pinning at connect time is NOT implemented; a porter hardening further should add a pinned resolver like georank's). Allowlist entries bypass even metadata-range blocks by design (operator escape hatch).
**Probe:** `grep -c "checkUrlIpAndHost" app/Misc/Helper.php` (= 3 — one caller in sanitizeRemoteUrl, one redirect-loop caller, one definition) and `grep -c "'fd00::/8'" app/Misc/Helper.php` (= 2).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-freescout", query: "checkUrlIpAndHost", limit: 5, fields: ["signature","name","file"] });
```
(line-exact: `Helper.checkUrlIpAndHost app/Misc/Helper.php 2097-2187`.)

## Direct tests (gate 3 evidence)
`tests/Unit/SsrfProtectionTest.php` pins ~30 host spellings end-to-end through `Helper::checkUrlIpAndHost`: decimal/octal/hex IPv4 encodings, IPv4-mapped IPv6, AWS-metadata addresses, `[::1]`, ULA ranges → all must return ''; only a public IPv6 literal and `example.org` pass through unchanged.

## Verdict
Adopt multi-representation candidate expansion + CIDR blocklist + canonical-IP gate + per-hop redirect revalidation; adapt curl specifics; omit nothing silently — if you drop the manual redirect loop you inherit a DNS-rebinding hole. Direct test: upstream SsrfProtectionTest.

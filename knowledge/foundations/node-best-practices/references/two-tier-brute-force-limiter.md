<!-- capsule-v2 -->
# Two-tier brute-force limiter — consecutive-fails-per-identity AND per-day-per-IP, both Redis-backed

**Source:** nodebestpractices CC-BY-SA-4.0 `master@dc3d60c2`; Codebase Memory `nodebestpractices`. **Question:** What limiter topology actually stops credential stuffing without locking out offices?

## username+IP pair (fast, short block) × IP total (slow, day block)
**Path/Symbol:** `sections/security/login-rate-limit.md` (:3-5 threat, :11-34 two-limiter config).
**Signature:** `new RateLimiterRedis({ storeClient, keyPrefix, points, duration, blockDuration })` — two instances with different key scopes.
**Data Shape:** limiter A: `login_fail_consecutive_username_and_ip`, points=10, duration=90 days (memory of first fail), blockDuration=1 hour. Limiter B: `login_fail_ip_per_day`, points=100/day, blockDuration=24 hours.

### Decisive source
```text
// login-rate-limit.md :11-13 — the two-tier contract
Create two limiters:
1. The first counts number of consecutive failed attempts and allows maximum
   10 by username and IP pair.
2. The second blocks IP address for a day on 100 failed attempts per day.
```

**Flow:** attacker sprays `/login` → tier-1 catches single-source attacks fast (10 consecutive wrong tries on ONE account from ONE machine ⇒ 1h lockout) → distributed attackers rotating usernames still exhaust tier-2's 100-fails/day IP budget ⇒ full-day block. Shared Redis store makes counts global across app instances.
**Invariant:** the tiers answer DIFFERENT attack shapes — targeted-account vs spray — which is why neither alone suffices. Keying tier-1 on the PAIR (not username alone) prevents an attacker from locking victims out by failing logins deliberately (DoS-on-account); keying tier-2 on IP accepts NAT trade-offs (whole office shares budget) at 100/day headroom.
**Probe:** no runner upstream. Deterministic probe: `grep -c 'maxWrongAttemptsByIPperDay\|maxConsecutiveFailsByUsernameAndIP' sections/security/login-rate-limit.md` >= 4 && `grep -c 'RateLimiterRedis' sections/security/login-rate-limit.md` >= 1.
**Retrieve:** **Retrieve:** doc-shaped/BM25-gap note — `search_graph` text queries return ZERO on this graph (Section nodes carry no searchable tokens); use `search_code`, executed live:
```bash
codebase-memory-mcp cli search_code '{"project": "nodebestpractices", "pattern": "maxConsecutiveFailsByUsernameAndIP", "limit": 10}'
# resolves `sections/security/login-rate-limit.md` line-exact (verified 2026-08-24)
```

## Verdict
Adopt the two-tier shape for any auth surface. Adapt thresholds to traffic profile; move store to any shared backend. Pair with general throughput limiting (`request-throttling-and-payload-caps`) — brute-force protection and overload protection are separate contracts.

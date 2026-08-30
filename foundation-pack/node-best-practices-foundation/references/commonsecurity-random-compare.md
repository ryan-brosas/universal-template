<!-- capsule-v2 -->
# Constant-time compare + CSPRNG — the two crypto primitives everyone reimplements wrong

**Source:** nodebestpractices CC-BY-SA-4.0 `master@dc3d60c2`; Codebase Memory `nodebestpractices`. **Question:** Why do `===` on hashes and custom random-string functions both fail, and what replaces them?

## timingSafeEqual for every secret comparison; crypto.randomBytes for every token
**Path/Symbol:** `sections/security/commonsecuritybestpractices.md` (timing-safe compare :17-21, random strings :25-29) + `sections/security/lintrules.md` (`detect-pseudoRandomBytes` rule :11-15).
**Signature:** `crypto.timingSafeEqual(a, b)` (Node >= 6.6.0); `crypto.randomBytes(size[, callback])`.
**Data Shape:** both take Buffers; timingSafeEqual returns boolean but keeps comparing through mismatches; randomBytes draws OS entropy.

### Decisive source
```text
// commonsecuritybestpractices.md :19 — why === dies
The default equality comparison methods would simply return after a character
mismatch, allowing timing attacks based on the operation length.
// :27 — why custom generators die
Using a custom-built function generating pseudo-random strings for tokens ...
might actually not be as random as you think, rendering your application
vulnerable to cryptographic attacks.
```

**Flow:** HMAC/hash check → attacker measures response-time deltas byte-by-byte → reconstructs secret prefix-by-prefix; timingSafeEqual removes the oracle by constant-time full compare. Token generation via `Math.random()`/custom PRNG → predictable seeds → session tokens forgeable; randomBytes uses kernel entropy instead.
**Invariant:** the failure mode is silent — code works, tests pass, only the attack surface differs. eslint-plugin-security ships named detectors for exactly these (`detect-pseudoRandomBytes`, plus `detect-eval-with-expression`, `detect-non-literal-fs-filename`, `detect-non-literal-regexp`) so the check belongs in CI lint, not review.
**Probe:** no runner upstream. Deterministic probe: `grep -c 'timingSafeEqual' sections/security/commonsecuritybestpractices.md` >= 1 && `grep -c 'randomBytes' sections/security/commonsecuritybestpractices.md sections/security/lintrules.md` >= 2.
**Retrieve:** **Retrieve:** doc-shaped/BM25-gap note — `search_graph` text queries return ZERO on this graph (Section nodes carry no searchable tokens); use `search_code`, executed live:
```bash
codebase-memory-mcp cli search_code '{"project": "nodebestpractices", "pattern": "timingSafeEqual", "limit": 10}'
# resolves `sections/security/commonsecuritybestpractices.md` line-exact (verified 2026-08-24)
```

## Verdict
Adopt both primitives as org-wide rules (lint-enforced). Adapt: pair with `password-kdf-ladder` (same doc bans Math.random for password material). Omit nothing — no safe subset exists of either.

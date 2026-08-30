<!-- capsule-v2 -->
# Password KDF selection ladder — bcrypt vs scrypt vs PBKDF2: which minimums, which salt rule, which trap?

**Source:** nodebestpractices CC-BY-SA-4.0 `master@dc3d60c2`; Codebase Memory `nodebestpractices`. **Question:** Which hash function and parameters for stored passwords, and what silently breaks each choice?

## Three-tier ladder with pinned minimums; salt always; Math.random never
**Path/Symbol:** `sections/security/userpasswords.md` (ladder :5-11, bcrypt example :15-32, scrypt :34-50, PBKDF2 :52-74, salting :100-107, pre-hash :108-112, randomness :114-116).
**Signature:** `bcrypt.hash(pw, cost)` / `bcrypt.compare(pw, hash)`; `crypto.scryptSync(pw, salt, outSize)`; `crypto.pbkdf2Sync(pw, salt, iterations, digest, outSize)`.
**Data Shape:** minimums — bcrypt `cost:12` (passwords <64 bytes); scrypt `N:32768, r:8, p:1`; PBKDF2 `iterations >= 10000, length {salt:16, password:32}`.

### Decisive source
```text
// userpasswords.md :7-9 — the ladder with floors
- bcrypt ... (minimum: cost:12, password lengths must be <64)
- scrypt ... (minimums: N:32768, r:8, p:1)
- PBKDF2 ... (minimums: iterations: 10000, length:{salt: 16, password: 32})
// :11 — the absolute prohibition
(NOTE: Math.random() should never be used as part of any password or token
generation due to its predictability.)
```

**Flow:** default to bcrypt (widest support, tunable rounds); need unlimited-length passwords or no native dependency → scrypt; FIPS/compliance mandate → PBKDF2. Salt is ALWAYS required (:5, :100): "reproducible data, unique to the user and your system" — e.g. username+app-name composite.
**Invariant:** THE TRAP a porter gets wrong: bcrypt's 64-byte input limit truncates long passwords AND long salts (:102) — scrypt is the escape hatch. Argon2 (OWASP/IETF winner) was pending native-crypto addition at doc time; when available it takes precedence. Randomness belongs to the algorithm, not to you — even avoid hand-rolled `crypto.random()` calls for passwords/tokens (see `commonsecurity-random-compare`).
**Probe:** no runner upstream. Deterministic probe: `grep -c 'cost:12\|N:32768' sections/security/userpasswords.md` >= 2 && `grep -c 'Math.random()' sections/security/userpasswords.md` >= 1.
**Retrieve:** **Retrieve:** doc-shaped/BM25-gap note — `search_graph` text queries return ZERO on this graph (Section nodes carry no searchable tokens); use `search_code`, executed live:
```bash
codebase-memory-mcp cli search_code '{"project": "nodebestpractices", "pattern": "Math.random", "limit": 10}'
# resolves `sections/security/userpasswords.md` line-exact (verified 2026-08-24)
```

## Verdict
Adopt the ladder order + minimum floors verbatim as config defaults. Adapt salt composition to your user model. Omit pre-hashing (front-end sha-256 hex) unless you specifically need unlimited client passwords AND can carry its administrative burden.

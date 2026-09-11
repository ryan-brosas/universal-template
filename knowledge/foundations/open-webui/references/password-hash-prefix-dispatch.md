<!-- capsule-v2 -->
# Password hash prefix-dispatch — how do you migrate password hashing algorithms without breaking stored hashes?

**Source:** open-webui "Open WebUI License" (BSD-3-Clause base + branding condition; citations-only) `main@01f4282f1ffe0d6212f58d3afbeae21fffd0c4be`; Codebase Memory `open-webui`. **Question:** When the configured hashing algorithm changes (bcrypt → argon2), how do existing stored hashes keep verifying, and how do you keep a 72-byte-limited legacy algorithm from silently truncating new passwords?

## Hashing follows config; verification follows the hash prefix
**Path/Symbol:** `backend/open_webui/utils/auth.py:get_password_hash` (168-177) + `verify_password` (194-216).
**Signature:** `async def get_password_hash(password: str) -> str`; `async def verify_password(plain_password: str, hashed_password: str) -> bool`.
**Data Shape:** algorithm from env `PASSWORD_HASH_ALGORITHM` (default `'bcrypt'`, `.lower()`ed, env.py:769); unknown value raises ValueError at hash time; `PASSWORD_BCRYPT_MAX_BYTES = 72` is defined in auth.py:49, NOT env.py.

### Decisive source
```python
if hashed_password.startswith('$argon2'):
    from argon2 import PasswordHasher
    from argon2.exceptions import InvalidHashError, VerificationError

    try:
        return await asyncio.to_thread(PasswordHasher().verify, hashed_password, plain_password)
    except (InvalidHashError, VerificationError):
        return False

password_bytes = plain_password.encode('utf-8')[:PASSWORD_BCRYPT_MAX_BYTES]
try:
    return await asyncio.to_thread(
        bcrypt.checkpw,
        password_bytes,
        hashed_password.encode('utf-8'),
    )
except ValueError:
    return False
```
(auth.py 199-216)

**Flow:** verify dispatches on the STORED HASH's `$argon2` prefix — not on the configured algorithm — so a fleet that flips `PASSWORD_HASH_ALGORITHM` to argon2 keeps verifying every existing bcrypt hash until each user next changes their password (which re-hashes with the new algorithm). The bcrypt arm truncates the PLAIN input to 72 bytes before checking, matching what bcrypt itself would have truncated at hash time.
**Invariant:** verification must be a pure function of the stored hash plus the candidate password; the configured algorithm may only steer NEW hashes. Any design that reads the env var in the verify path breaks every pre-migration account the moment the flag flips.

## Asymmetric 72-byte policy: reject new, truncate old
**Path/Symbol:** `auth.py:validate_password` (180-191) vs `verify_password` (:208).
**Signature:** `def validate_password(password: str) -> bool` (raises on policy violation).
**Data Shape:** new bcrypt passwords > 72 UTF-8 bytes ⇒ `ERROR_MESSAGES.PASSWORD_TOO_LONG`; stored-hash verification truncates to 72 bytes instead.

### Decisive source
```python
# bcrypt only accepts 72 bytes; reject long new passwords instead of storing an unusable hash.
if PASSWORD_HASH_ALGORITHM == 'bcrypt' and len(password.encode('utf-8')) > PASSWORD_BCRYPT_MAX_BYTES:
    raise Exception(
        ERROR_MESSAGES.PASSWORD_TOO_LONG,
    )
```
(auth.py 181-185)

**Flow:** at set/change time, `validate_password` rejects over-long passwords for the CURRENTLY CONFIGURED algorithm (storing a bcrypt hash of a >72-byte password would bake in a silent truncation the user never consented to); at check time, `verify_password` still truncates so legacy rows created before the guard existed keep working. A separate `ENABLE_PASSWORD_VALIDATION` regex gate (env.py:768) runs after the length gate when enabled.
**Invariant:** the write path must be STRICTER than the read path for byte-limited algorithms — reject new input the algorithm would mangle, but never fail to verify data the system itself once accepted.

## Off-loop crypto, boolean failures
**Path/Symbol:** `auth.py` :173/:175/:204/:210.
**Data Shape:** every bcrypt/argon2 call wrapped in `asyncio.to_thread`; verify returns False (never raises) on empty hash, InvalidHashError, VerificationError, or ValueError.

### Decisive source
```python
if not hashed_password:
    return False
```
(auth.py 196-197)

**Flow:** empty/None stored hash short-circuits to False before any crypto; all blocking work leaves the event loop via `asyncio.to_thread` (bcrypt is CPU-bound and would stall the loop for tens of ms per attempt); library exceptions are caught per-algorithm and mapped to False.
**Invariant:** a corrupt or foreign-format hash must look like "wrong password", not a 500 — both for UX and so the error channel can't distinguish "no such row" from "malformed hash".
**Probe:** no upstream tests exist at this pin (zero test files repo-wide — recorded block). Deterministic anchors: `grep -n "startswith('$argon2')" backend/open_webui/utils/auth.py` → 199; `grep -n "PASSWORD_BCRYPT_MAX_BYTES = 72" backend/open_webui/utils/auth.py` → 49; `grep -n "len(password.encode('utf-8')) > PASSWORD_BCRYPT_MAX_BYTES" backend/open_webui/utils/auth.py` → 182; `grep -n "PASSWORD_HASH_ALGORITHM" backend/open_webui/env.py` → 769.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "open-webui", query: "get_password_hash verify_password argon2 bcrypt prefix", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt prefix-dispatched verification (stored hash decides the algorithm), config-steered hashing, the asymmetric reject-new/truncate-old byte-limit policy, off-loop crypto, and boolean-failure mapping. Adapt the algorithm set and the max-bytes constant to your chosen KDFs. Omit open-webui's lazy in-function imports unless you want optional dependencies to stay optional at module load. Coverage caveat: all cited paths are graph-clean (`no_recorded_issue`, metadata_match) but have no upstream tests; claims pinned by direct source reads at the lines cited above.

<!-- capsule-v2 -->
# Timing-Equalized Argon2 Login — how does an unknown-email login cost exactly as much as a known one?

**Source:** awaithumans Apache-2.0 `main@bc05b8e7`; Codebase Memory `mnt-hdd-utopia-inspo-awaithumans`. **Question:** How do you stop argon2's ~100ms verify cost from leaking account existence through login latency?

## Pre-computed dummy hash burns identical CPU on the miss path
**Path/Symbol:** `packages/python/awaithumans/server/core/password.py` — `_hasher` singleton (:32), `_DUMMY_HASH` (:38), `verify_password` (:46–55), `dummy_verify` (:58–70).
**Signature:** `hash_password(password: str) -> str` (PHC format); `verify_password(password: str, stored_hash: str) -> bool`; `dummy_verify(password: str) -> None`.
**Data Shape:** one module-level `PasswordHasher()` (threadsafe, expensive to construct per-call); dummy hash computed once AT IMPORT over `"*timing-equalization-sentinel*"`.

### Decisive source
```python
_DUMMY_HASH = _hasher.hash("*timing-equalization-sentinel*")

def verify_password(password: str, stored_hash: str) -> bool:
    try:
        return _hasher.verify(stored_hash, password)
    except VerifyMismatchError:
        return False
    except Exception as exc:  # malformed hash, unexpected algorithm
        logger.warning("password verify failed (treated as mismatch): %s", exc)
        return False

def dummy_verify(password: str) -> None:
    # Any outcome is fine; we just wanted the CPU spend.
    with contextlib.suppress(Exception):
        _hasher.verify(_DUMMY_HASH, password)
```

**Flow:** known-user branch = real verify; unknown-user branch = `dummy_verify(password)` — verifies the SUBMITTED password against the fixed sentinel hash so CPU time matches. Result discarded.
**Invariant:** malformed/unexpected hashes are treated as mismatch (False + warning), never raised — callers see only "wrong password". The sentinel string must be unpredictable ("no real user can ever match it"). Defaults left at argon2-cffi values (= RFC 9106 minimums), deliberately untuned.
**Probe:** `packages/python/tests/users/test_security_guards.py:106` `test_dummy_verify_takes_comparable_time_to_real_verify` — the timing property itself is pinned upstream.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-awaithumans", query: "dummy_verify verify_password hash_password PasswordHasher", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt import-time dummy-hash precomputation and the swallow-everything dummy verify verbatim. Adapt only the hasher construction if your framework already provides one. Omit nothing else — the timing test upstream means any "optimization" that skips the dummy burn is a detectable regression.

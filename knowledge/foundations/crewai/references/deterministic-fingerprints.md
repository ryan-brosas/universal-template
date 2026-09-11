<!-- capsule-v2 -->
# Deterministic fingerprint identity — uuid5-seeded stable IDs for agents/crews/tasks

**Source:** crewAI MIT `main@9e9a8577`; Codebase Memory `ext-crewAI`. **Question:** How do components get stable, reproducible identifiers for tracking/auditing across process restarts — and what does the seed control vs leave random?

## Connected graph-selected seam
**Path/Symbol:** `lib/crewai/src/crewai/security/fingerprint.py` — `Fingerprint` (:41), `_generate_uuid` (:76), `generate` (:91); namespace in `security/constants.py:CREW_AI_NAMESPACE`; seed plumbing via `security/security_config.py`.
**Signature:** `Fingerprint.generate(seed: str | None = None, metadata: dict | None = None) -> Self`; `_generate_uuid(seed) -> str = str(uuid5(CREW_AI_NAMESPACE, seed))`.
**Data Shape:** dual identity — human-readable id (derived from role when unspecified) + fingerprint uuid; uuid/timestamp are PrivateAttrs set through `fingerprint.__dict__["_uuid_str"]` to bypass pydantic field machinery.

### Decisive source
```python
# :76 deterministic branch
def _generate_uuid(cls, seed: str) -> str:
    if not seed.strip():
        raise ValueError("Seed cannot be empty or whitespace")
    return str(uuid5(CREW_AI_NAMESPACE, seed))

# :104 same instance gets either random or derived uuid AFTER construction
fingerprint = cls(metadata=metadata or {})
if seed:
    fingerprint.__dict__["_uuid_str"] = cls._generate_uuid(seed)
return fingerprint

# :17 metadata guard — one nesting level, 10KB string-length budget
if len(str(v)) > 10_000:
    raise ValueError("Metadata size exceeds maximum allowed (10KB)")
```

**Flow:** SecurityConfig(fingerprint=<seed-string>) → validator converts to Fingerprint via generate(seed) → Agent/Crew/Task copy that fingerprint so a whole hierarchy shares one root identity; re-creating components with the SAME seed yields byte-identical uuid_str but FRESH created_at timestamps. Equality/hash compare ONLY uuid_str.
**Invariant:** uuid5 determinism requires BOTH the fixed CREW_AI_NAMESPACE and the seed — porting with a random namespace silently breaks cross-restart correlation tests. Empty/whitespace seeds raise rather than degrade to random. Metadata validation is shallow-by-design (dict-of-one-level) with a crude size cap.
**Probe:** `grep -c 'uuid5' lib/crewai/src/crewai/security/fingerprint.py` → `2`; `grep -c '10_000' lib/crewai/src/crewai/security/fingerprint.py` → `1`.
**Direct test:** `tests/security/test_deterministic_fingerprints.py::test_basic_deterministic_fingerprint` (:9 asserts equal uuids AND different created_at), `::test_security_config_with_seed_string` (:165 propagates through Agent).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-crewAI", query: "Fingerprint generate deterministic UUID seed agents", limit: 5 });
// → ext-crewAI...security.fingerprint.Fingerprint Class fingerprint.py 41+
```

## Verdict
Adopt namespaced-uuid5 seeded identity + separate created_at for any multi-agent audit trail. Adapt namespace constant and metadata limits. Omit crewai's role-based human-readable-id derivation if host has its own naming.

<!-- capsule-v2 -->
# Docs-as-deployed-contract — why do the marketing README and template README restate the security and sizing facts the entrypoint enforces?

**Source:** railway-template-nexus3 EPL-1.0 `main@18e177a6563436ca1cd7e44bc2fa5648f6735c58`; Codebase Memory `railway-template-nexus3`. **Question:** What do human-facing docs contribute to a deployment template's correctness surface, beyond onboarding?

## Doc claims mirror runtime invariants
**Path/Symbol:** `README.md:5` ("generated administrator password, anonymous access disabled"), `README.md:7` (EULA wizard + "The template does not accept legal terms on your behalf"; ≥2 GB RAM; one replica; `/nexus-data`), `TEMPLATE_README.md:23` ("The adapter waits for first boot, rotates ... through the official API, disables anonymous access, and stores an idempotency marker").
**Signature:** prose, no code — but each claim names a mechanism that EXISTS in code: rotation+anonymous-off+marker = `entrypoint.sh:19-21`; consent refusal = `scripts/smoke.py:8-10`; sizing = `railway.toml` + embedded-DB topology.
**Data Shape:** three claim families: (1) SECURITY FACTS (what hardening runs at first boot); (2) CONSENT POSTURE (who accepts legal terms — humans in the wizard, never the template); (3) TOPOLOGY CONSTRAINTS (≥2 GB RAM, ONE replica, persistent `/nexus-data`).

### Decisive source
```markdown
The adapter waits for first boot, rotates the generated bootstrap password
through the official API, disables anonymous access, and stores an
idempotency marker. Use one replica and at least 2 GB RAM.
```

**Flow:** TEMPLATE_README.md:23 is the human-language twin of the bootstrap ladder: rotate → disable-anonymous → marker (exactly `entrypoint.sh:19→20→21` in order). README:7 carries the same contract to operators plus the consent posture mirrored by the smoke script's opt-in gate.
**Invariant:** doc claims are CONTRACT, not decoration: they are what a deploying operator relies on when deciding whether the deployment is safe. If code changes (different endpoints, different marker name), the docs' factual claims must move in the same commit or the template ships false advertising. Conversely the docs constrain implementation: "stores an idempotency marker" means a porter may NOT replace the marker with a re-run-on-every-boot design without breaking published behavior. The EULA sentence is the human-side half of `eula-consent-gate`'s automation gate — two surfaces, one policy: nobody accepts legal terms by default.
**Probe:** EXECUTED this pass: `grep -cF 'idempotency marker' TEMPLATE_README.md` = 1, `grep -cF '/nexus-data' README.md` = 1, `grep -cF '2 GB' README.md` = 1, `grep -cF '2 GB' TEMPLATE_README.md` = 1, `grep -cE 'not accept.*on your behalf|not accept legal terms' README.md` = 1, same for TEMPLATE_README.md = 1, `grep -icF 'trademark' README.md THIRD_PARTY_NOTICES.md` = 2 files ×1.

## Get live surrounding code
**Retrieve:** search_code resolves the doc twin directly:
```
codebase-memory-mcp cli search_code '{"project":"railway-template-nexus3","pattern":"idempotency","limit":4}'
```
→ Module `TEMPLATE_README` L1-28 match at `"23"` (verified this pass).

## Verdict
Adopt: treat user-facing docs as part of the deployment contract — every factual security/sizing/consent claim must have a code twin, and mechanism-changing edits must move both together. Adapt claims per product. Omit pure-marketing sections from the contract set.

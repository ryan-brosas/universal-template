<!-- capsule-v2 -->
# Hierarchical env-aware config — which five properties must a config solution combine?

**Source:** nodebestpractices CC-BY-SA-4.0 `master@dc3d60c2`; Codebase Memory `nodebestpractices`. **Question:** What does the repo require of configuration beyond "use process.env", and where does startup fail-fast enter?

## Files+hierarchy+env-overrides+secret-exclusion+startup validation (convict-class); fail at boot on missing keys
**Path/Symbol:** `sections/projectstructre/configguide.md` (:7 five numbered requirements), (:21+ hierarchical json5 example).
**Signature:** hierarchical config file grouped by section (`{"Customer": {"dbConfig": {...}}}`) → overridden by process env vars → sensitive entries either encrypted, commit-encrypted, or placeholder-filled at deploy; validation via `convict` at startup.
**Data Shape:** three sources unioned at runtime — committed files (dev convenience), environment variables (ops authority), CLI/centralized-store injections for advanced scenarios.

### Decisive source
```text
# configguide.md :7 — requirement 5 is the gate most ports skip
5. the application should fail as fast as possible and provide the immediate
feedback if the required environment variables are not present at start-up,
this can be achieved by using [convict] to validate the configuration.
```

**Flow:** flat-file-only fails at ~100 keys (unfindable) and files-only locks out DevOps edits (:7.1) → hierarchical sections + multi-file union solve scale → env vars override per environment → secrets NEVER live in the file (encrypt/placeholder/inject) → schema validation at boot throws immediately on missing required values.
**Invariant:** config errors are STARTUP errors — an app that boots with missing config has already failed the contract ("fail as fast as possible... at start-up"). Pairs with `secrets-env-and-npm-publish` (env-var litmus) and `failfast-and-error-flow-tests` (same throw-early doctrine applied to deployment inputs).
**Probe:** no runner upstream. Deterministic probe: `grep -c convict sections/projectstructre/configguide.md` >= 2 && `grep -c 'fail as fast as possible' sections/projectstructre/configguide.md` >= 1.
**Retrieve:** `await mcp.codebase_memory.search_code({ project: "nodebestpractices", pattern: "convict", limit: 5 });`

## Verdict
Adopt the five-property checklist and boot-time validation as acceptance criteria for any config loader. Adapt library (rc/nconf/config/convict named; zod-validated env modules are the modern twin). Omit library feature matrices.

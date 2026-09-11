<!-- capsule-v2 -->
# Env-gate fail-closed ordering — why must the required-secret check be the FIRST statement the entrypoint runs?

**Source:** railway-template-nexus3 EPL-1.0 `main@18e177a6563436ca1cd7e44bc2fa5648f6735c58`; Codebase Memory `railway-template-nexus3`. **Question:** How does a deployment template guarantee a missing operator secret produces a clean instant failure instead of a booted-but-unrotated service?

## `${VAR:?msg}` gate before any side effect
**Path/Symbol:** `entrypoint.sh:3` (the gate), `entrypoint.sh:2` (`set -eu` making the expansion fatal), `entrypoint.sh:4-5` (first side effects, strictly after the gate).
**Signature:** POSIX parameter expansion `: "${NEXUS_ADMIN_PASSWORD:?NEXUS_ADMIN_PASSWORD is required}"` — the leading `:` discards the expanded value; only the expansion's side effect (abort on unset/empty) matters.
**Data Shape:** Input: environment variable `NEXUS_ADMIN_PASSWORD` (operator-chosen admin secret). Failure shape: shell exits nonzero printing `NEXUS_ADMIN_PASSWORD is required` to stderr; zero filesystem/network mutations.

### Decisive source
```sh
set -eu
: "${NEXUS_ADMIN_PASSWORD:?NEXUS_ADMIN_PASSWORD is required}"
mkdir -p /nexus-data
chown -R 200:200 /nexus-data
```

**Flow:** `set -eu` arms errexit → the `:?` expansion aborts the shell when the variable is unset OR empty → this happens BEFORE `mkdir`/`chown`/marker checks/server spawn → a misconfigured deploy dies in milliseconds with the variable name as the error message.
**Invariant:** no observable side effect precedes the config gate. A porter who moves validation "later, near first use" creates the worst failure mode this template exists to prevent: the JVM boots fully (minutes, 2 GB RAM), the rotation PUT then fails or never fires, and the registry sits reachable with its GENERATED admin password printed in a volume file — silently insecure, and the 900 s bootstrap budget is burned discovering it. Fail-closed-at-start converts config errors into loud instant platform-visible failures (which the ON_FAILURE×10 policy surfaces as repeated crash-loops, not silent exposure).
**Probe:** EXECUTED by this pass (see signal-relay-dual-path): `env -u NEXUS_ADMIN_PASSWORD sh entrypoint.sh` → nonzero exit, stderr `NEXUS_ADMIN_PASSWORD is required`, and — because the gate is line 3 — provably no `/nexus-data` mutation. Static pin candidate: `grep -c ': "' entrypoint.sh` ≥ 1 with the gate on the first executable line.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "railway-template-nexus3", query: "ADMIN_PASSWORD required env", limit: 10 });
```
(Resolves the `__env__ADMIN_PASSWORD` EnvVar node — the graph's record of this contract; shell ordering itself is source-confirmed.)

## Verdict
Adopt the ordering contract: required-env assertion as the first executable statement of any mutating bootstrap script, implemented with `${VAR:?msg}` under `set -eu`. Adapt the variable name/message per product. Omit nothing. Note the deliberate reuse: the SAME variable is consumed twice (rotation target at `:19`, subsequent auth at `:20`) — the gate guarantees both uses see a non-empty value. Coverage caveat: upstream's static suite does not pin this line; the probe above is this foundation's direct behavioral evidence.

<!-- capsule-v2 -->
|# Dry-run mode + per-run application cap — how do I make a job-application bot safe to test and self-limiting in production?

**Source:** EasyApplyJobsBot CC **BY-NC-SA 4.0 — learn-only: pattern + control-flow recorded, no verbatim code reuse** `main@70fe748` (2026-03-29); Codebase Memory `EasyApplyJobsBot`. **Question:** what two cheap gates turn an auto-submitting bot into something you can dry-run against live LinkedIn and that stops itself before tripping daily-action limits?

## The two safety gates in the submit path
**Path/Symbol:** `config.py:dryRun` (:130) + `maxApplicationsPerRun` (:133); consumed at `linkedin.py:linkJobApply` (:235–247 one-step path, :261–271 multi-step path, :283–294 triple-break + stop banner); `applyProcess` (:477–480 pre-review gate).
**Signature:** module-level config flags: `dryRun: bool = False`, `maxApplicationsPerRun: int = 0` (0 = unlimited); runtime counter `countApplied` compared AFTER each increment.
**Data Shape:** every outcome is a string result line routed through ONE channel (`displayWriteResults` → console + dated file): `"* 🧪 DRY RUN - Would apply..."` vs `"* 🥳 Just Applied to this job: <url>"`; cap check is truthiness-guarded (`if config.maxApplicationsPerRule and countApplied >= ...`) so 0 cleanly disables.

### Decisive source (control flow, paraphrased — NC license)
```python
# ONE-STEP PATH: choose log-vs-submit at the last possible moment
if config.dryRun:
    lineToWrite = "... DRY RUN - Would apply to this job: " + offerPage   # log only
else:
    click("button[aria-label='Submit application']")                       # real action
    countApplied += 1
    if config.maxApplicationsPerRun and countApplied >= config.maxApplicationsPerRun:
        reachedCap = True
# MULTI-STEP PATH: same gate BEFORE 'Review your application' — walk all steps,
# fill everything, then decline to press Review/Submit
# TERMINATION: reachedCap breaks THREE nested loops (jobID / page / url) via
# stacked `if reachedCap: break`, then prints "Reached max applications per run"
```
**Flow:** navigate + fill everything normally → at each would-submit point branch on dryRun (log instead of act) → on real submits increment and compare to cap → triple-break out of all loops → session summary still printed.
**Invariant:** dry-run must exercise the FULL navigation/form-fill path (selectors are validated by walking, not stubbed) and differ ONLY at the irreversible verb (submit/review); the cap is checked after increment with a truthy guard so `0` means unlimited, not unreachable; both paths funnel results through one string channel so logs stay comparable between dry and live runs.
**Probe:** repo has no automated tests — coverage caveat. Deterministic probe: `grep -n "dryRun\|maxApplicationsPerRun" linkedin.py` hits exactly the three decision points + banner; config defaults (`False`, `0`) keep production behavior unchanged.
**Retrieve:** `await mcp.codebase_memory.search_graph({ project: "EasyApplyJobsBot", query: "dryRun maxApplicationsPerRun linkJobApply", limit: 5 });`

## Verdict
Adopt the pattern: a boolean dry-run flag consulted at EVERY irreversible action point (not just once at top level), a post-increment run cap with truthy-zero-means-unlimited semantics, and stacked loop breaks for immediate full-stop. Adapt threshold values (LinkedIn's own guidance ≈ under 200 applications/day) and route dry-run output into the same ledger as live runs so a dry run is diffable against a live one. Omit this repo's hard-coded emoji/string outcomes as an API (NC-licensed); reimplement with typed result enums. Contrast: dedupe-applied-tracking prevents RE-processing across runs; these two gates bound what a SINGLE run may do — cross-run state and intra-run caps are complementary safety layers.

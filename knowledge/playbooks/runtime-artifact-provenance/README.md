---
title: runtime-artifact-provenance
summary: "Use when a fix is absent from a running app despite a successful build or install; distinguish the built artifact, installed copy, and loaded runtime before editing again. Includes Linux executable-identity probes and restart boundaries."
kind: playbook
---

# Verify the artifact a running app uses

Build success, installation, and runtime activation are separate claims. An
installer can replace an executable's directory entry while an existing process
keeps the old file open. A green source-level test then says nothing about the
window the user is inspecting.

## Trace the consumer before rebuilding

1. **Identify the instance.** Resolve the user's launcher, service unit, or container
   to the actual process and expected artifact path. Enumerate instances with PID,
   parent, command, and start time; associate the visible window or failing endpoint
   with one. Broad command-line matching also finds diagnostic shells: validate
   candidates rather than taking the first few matches.
2. **Separate build, install, and load.** Compare build IDs or hashes of the verified
   build output and installed copy. Then compare the loaded artifact. A different
   installed build calls for installation diagnosis; an obsolete loaded build calls
   for activation diagnosis. Only after these agree does repeating source-level
   debugging address the tested runtime.
3. **Use independent evidence.** On Linux, set `pid` to a validated application PID
   and `artifact` to its expected installed executable:

   ```bash
   ps -p "$pid" -o pid=,ppid=,lstart=,comm=
   readlink "/proc/$pid/exe"
   stat -Lc '%d:%i %y' "/proc/$pid/exe" "$artifact"
   sha256sum "/proc/$pid/exe" "$artifact"
   ```

   `(deleted)` means the executable file was unlinked, not necessarily upgraded or
   corrupted. Different device/inode identities prove different files, not different
   contents; equal hashes can identify an identical reinstall. A process starting
   **before** an install is a clue, not proof: timestamps may be preserved, and
   loading behavior differs. Hashes/build IDs corroborate identity within the
   artifacts compared. Revalidate the PID if it exits or restarts during inspection.

   An uncompressed, distinctive literal can be supporting evidence:

   ```bash
   grep -aF -- "$marker" "/proc/$pid/exe" >/dev/null
   grep -aF -- "$marker" "$artifact" >/dev/null
   ```

   Inspect exit status: 0 means found, 1 absent, greater than 1 a probe error.
   A marker's presence does not prove its code executed or that the fix works;
   absence is inconclusive if bundling, stripping, or compression can remove it.

## Match the evidence to what is loaded

For scripts, `/proc/$pid/exe` identifies the interpreter, not the script. Native
addons, JS/CSS bundles, served assets, and cached modules need their own identity
checks. A container image digest does not prove which mounted configuration the
app consumed. Starting after a config write establishes ordering, not successful
loading; use application readback or startup evidence when available. Report
permissions, namespaces, or unavailable runtime IDs as limits, not mismatches.

At a child-process or delegated-runner boundary, verify the identities material
to the claim in that consumer: resolved artifacts, effective configuration and,
where relevant, the model that actually served its requests. Parent verification
does not prove inheritance. Record intentional differences; leave unavailable
identity unknown. Reuse established evidence for unchanged in-process consumers
rather than inventorying every helper.

## Activate safely, then verify behavior

List direct children with `pgrep -a -P "$pid"`; inspect descendants and lifecycle
ownership where relevant. Stopping a parent may orphan children, gracefully stop
them, or trigger supervisor/cgroup cleanup. Parentage alone proves neither active
work nor recoverability. Prefer the app's normal quit/restart flow; explain affected
windows, workers, and possible interruption before obtaining restart approval.
For supervised services use
[local-service-durability](../local-service-durability/README.md).

After authorized activation through the user's launcher, recheck artifact identity
and reproduce the original symptom. Finding a stale artifact is not proof that
restarting will fix the symptom. If the loaded artifacts are current,
continue [debugging](../debugging-and-error-recovery/README.md). Keep provenance
verified and behavior verified separate in the final report.

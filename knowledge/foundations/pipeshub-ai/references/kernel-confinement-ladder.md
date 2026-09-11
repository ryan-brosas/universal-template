<!-- capsule-v2 -->
# Kernel confinement degrade ladder — how does Seatbelt/bwrap wrap a subprocess tree without breaking hosts that lack it?

**Source:** pipeshub-ai Apache-2.0 `main@4a02110dd9a7a644d8ba7a5ccd295c58a3c3628f`; Codebase Memory `pipeshub-ai`. **Question:** How do you layer kernel-level confinement on a subprocess runner so unsupported platforms DEGRADE to plain isolation instead of failing?

## Probe-once, wrap-or-return-unchanged, warn once per platform
**Path/Symbol:** `backend/python/app/agent_loop_lib/sandbox/confinement.py:confine_command/_seatbelt_works/confinement_available` (L24–78); `_seatbelt_wrap` (L81–120); `_bubblewrap_wrap` (L123–140).
**Signature:** `confine_command(cmd: list[str], working_dir: str, allow_network: bool = False) -> list[str]` — SAME argv length contract as its input when degrading.
**Data Shape:** macOS → `sandbox-exec -p <inline profile> …`; Linux+bwrap → `bwrap --ro-bind / / --bind wd wd --tmpfs /tmp --dev /dev --proc /proc --unshare-all --die-with-parent [--share-net] -- cmd…`.

### Decisive source
```python
def _seatbelt_works() -> bool:      # probe ONCE, cache globally
    ...
    # macOS 14+ (Sonoma/Sequoia): unprivileged processes get EPERM from
    # sandbox_apply even though the binary exists at /usr/bin/sandbox-exec.
    result = subprocess.run(["sandbox-exec", "-p", "(version 1)(allow default)",
                             "/usr/bin/true"], capture_output=True, timeout=5)
    _seatbelt_probe_result = result.returncode == 0

# deny-by-default profile — the two clauses porters always get wrong:
network_clause = (
    "(allow network*)" if allow_network
    else "(deny network*)(allow network* (local unix))"
    # local unix sockets are process-local IPC (tsx loader hook, python
    # multiprocessing, local DB drivers) — ALWAYS allowed even with
    # network off, or tools die on listen()/connect() with confusing EPERM.
)
"(allow mach-lookup)"
# needed for TLS cert validation (trustd over Mach) and DNS (mDNSResponder) —
# WITHOUT it, allowing network* still fails HTTPS deep in the TLS handshake
# with cryptic OSStatus errors that look unrelated to sandboxing.
```

**Flow:** `confine_command` → darwin + probe-passed → seatbelt inline `-p` profile (deny default; exec/read everywhere; write ONLY under working_dir; sysctl-read; mach-lookup; network clause) → linux + bwrap present → bubblewrap arg set (ro-bind root, rw-bind sandbox dir only, unshare-all, die-with-parent so nothing outlives a kill) → otherwise return cmd UNCHANGED after one warning per platform string.
**Invariant:** (1) Degrade-gracefully is load-bearing: confinement availability varies by OS/version/entitlement, and a hard requirement would break every unsupported host — "works everywhere, hardened where possible". (2) The unix-socket carve-out and mach-lookup allowance are what keep network-off usable; removing either produces failures that look like app bugs. (3) Write scope is the sandbox's OWN realpath'd dir — deliberately NOT the shared system temp dir. (4) Probe result cached process-wide; bwrap presence checked per-call via `shutil.which`.
**Probe:** No direct unit suite imports `confinement` at HEAD (`grep -rl confine_command tests/` → none) — coverage caveat recorded; deterministic probes: source-symbol grep for `local unix`/`mach-lookup` clauses + `search_graph` retrieval of `confine_command`. Behavior on real macOS/Linux kernels is upstream-validated only.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pipeshub-ai", query: "confine_command _seatbelt_wrap _bubblewrap_wrap confinement_available", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the probe-cache-degrade ladder and both platform profiles verbatim (they encode hard-won macOS/Linux quirks); adapt the write-scoped path to your sandbox layout. Coverage caveat: no direct test file — treat the profile text itself as the spec and verify on-target before trusting.

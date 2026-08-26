<!-- capsule-v2 -->
# Soffice AF_UNIX Shim — how does LibreOffice run headless in a sandbox that blocks Unix sockets?

**Source:** anthropics/skills (source-available per LICENSE.txt) `main@3b3fad96`; Codebase Memory `mnt-hdd-utopia-inspo-reference-skills`. **Question:** What does the shared office helper do about blocked AF_UNIX, and why must callers use run_soffice rather than raw subprocess with the env?

## Runtime-probed LD_PRELOAD shim + mandatory profile injection
**Path/Symbol:** `skills/docx/scripts/office/soffice.py` — `get_soffice_env` (:27–35), `run_soffice` (:38–46), `_needs_shim` (:53–59), `_ensure_shim` (:62–74), embedded C shim source (:78–185). BYTE-IDENTICAL twin vendored across docx/xlsx/pptx `scripts/office/soffice.py` (graph shows identical line ranges 38–46/27–35 for all three).
**Signature:** `get_soffice_env() -> dict`; `run_soffice(args: Iterable[str], **kwargs) -> CompletedProcess`.
**Data Shape:** env always sets `SAL_USE_VCLPLUGIN=svp` (headless plugin); if a probe `socket(AF_UNIX, SOCK_STREAM)` raises OSError → env adds `LD_PRELOAD=/tmp/lo_socket_shim.so`, compiled once from an inline C string via `gcc -shared -fPIC -ldl`. Shim interposes socket/socketpair/listen/accept/close/read with per-FD tables sized 1024 (`is_shimmed`, `peer_of`, wake pipe pair per FD, single `listener_fd`).

### Decisive source
```python
def run_soffice(args, **kwargs):
    args = list(args)
    with contextlib.ExitStack() as stack:
        if not any(str(a).startswith("-env:UserInstallation") for a in args):
            profile = stack.enter_context(tempfile.TemporaryDirectory(prefix="lo_profile_", ...))
            args = [f"-env:UserInstallation={Path(profile).as_uri()}"] + args
        return subprocess.run(["soffice"] + args, env=get_soffice_env(), **kwargs)
```
```c
int close(int fd) {
    ...
    if (was_listener)
        _exit(0);                        /* conversion done – exit */
    return real_close(fd);
}
```

**Flow:** caller passes plain argv → run_soffice injects a throwaway `-env:UserInstallation=file://…` profile UNLESS the caller already supplied one (accept_changes.py deliberately supplies its own persistent macro profile) → get_soffice_env probes AF_UNIX; blocked ⇒ compile-once shim → soffice runs; when its internal socket(AF_UNIX) fails, the shim falls back to socketpair(); listen() is swallowed as success; accept() blocks on a wake-pipe read then returns ECONNABORTED; close() of the listener writes the wake byte and `_exit(0)`s so soffice terminates promptly after conversion.
**Invariant:** The module docstring is the load-bearing warning: `get_soffice_env()` alone names NO user profile, and in a non-root sandbox soffice cannot bootstrap its default one — it aborts with "User installation could not be completed" and converts NOTHING while exiting 0-looking paths; hence "call through run_soffice". Callers building custom argv MUST add -env:UserInstallation themselves. The `_exit(0)`-on-listener-close is the shutdown contract: conversions end by closing the IPC listener, not by process-exit bookkeeping.
**Probe:** No upstream tests. Deterministic probes (anchors re-derived & executed 2026-08-24): `grep -c '_exit(0)' skills/docx/scripts/office/soffice.py` = 1 (in C shim source); `grep -c 'UserInstallation' skills/docx/scripts/office/soffice.py` = 3; vendored-twin check executed this session: md5 of docx vs pptx copies identical.
**Coverage caveat:** sandbox-dependent integration surface; untested upstream.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-reference-skills", query: "run_soffice", limit: 6 });
// xlsx + docx + pptx scripts/office/soffice.py 38-46 (identical twins)
```

## Verdict
Adopt the pattern (probe→preload-shim→fallback semantics, throwaway-profile injection at ONE chokepoint) for any GUI-app-in-sandbox problem; adopt the docstring rule that wrapper functions must own ALL required argv/env so callers can't assemble a broken half-invocation. Adapt the shim to your libc/toolchain; omit entirely where AF_UNIX is allowed.

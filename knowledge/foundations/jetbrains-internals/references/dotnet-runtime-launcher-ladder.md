<!-- capsule-v2 -->
# .NET runtime launcher ladder — how does a JVM IDE resolve and exec its bundled .NET runtime across platform/libc/arch without a system dotnet?

**Source:** JetBrains Rider installed build `RD-262.8665.400` (`lib/ReSharperHost/runtime-dotnet.sh`, 30L whole; `lib/ReSharperHost/Rider.Backend.sh`, 6L whole); Codebase Memory `jetbrains-rider`. **Question:** Where a product hosts a second managed runtime, what is the minimal launcher that picks the right private runtime copy per platform × libc × architecture, and what OS friction must it absorb?

## The ladder as the decisive instance
**Path/Symbol:** `runtime-dotnet.sh:case $(uname)` ladder (:5-20), quarantine unblock :26-28.
**Signature:** `exec "$dotnet/dotnet" "$@"` after resolving `dotnet="$root/$platform-$architecture/dotnet"`.
**Data Shape:** inputs: `uname`, `uname -m`, optional `ldd --version` output, `getconf LONG_BIT`; output: exactly one of {macos-x64, macos-arm64, linux-x64, linux-musl-x64, linux-arm64, linux-musl-arm64, linux-arm} (all verified present as dirs beside the script; windows-* dirs exist but this script errors out on non-Darwin/Linux).

### Decisive source
```sh
Linux) platform=$({ ldd --version 2>&1 || true; } | grep -q musl && echo linux-musl || echo linux)
    case $(uname -m) in
    x86_64)          architecture=x64;;
    aarch64)         architecture=$([ $(getconf LONG_BIT) -eq 32 ] && echo arm || echo arm64);;
    armv7l | armv8l) architecture=arm;;
    *) echo "Unknown architecture: $(uname -m)" >&2; exit 2;;
    esac;;
...
# Unblock files when downloaded in Safari
if [ "x$platform" = "xmacos" ] && xattr "$dotnet" | grep -q com.apple.quarantine; then
  xattr -d -r com.apple.quarantine "$dotnet"
fi
exec "$dotnet/dotnet" "$@"
```

**Flow:** detect OS family → on Linux probe libc by grepping `ldd --version` for musl (the only portable libc discriminator; failure-safe via `|| true`) → map machine arch, demoting arm64 to arm when userspace is 32-bit (`LONG_BIT`=32) → point at the PRIVATE runtime copy under the resolved dir → macOS-only: strip Safari's quarantine xattr recursively before first exec → hand off with exec so signals/exit codes pass through.
**Invariant:** the script never falls back to a system dotnet and never guesses: unknown combos exit non-zero with stderr text. libc detection must precede path resolution because musl and glibc runtimes are NOT interchangeable. Wrong port: using `uname -o` or checking Alpine's /etc/os-release — the shipped check keys on ldd itself, which works on any distro.
**Probe:** deterministic layout probe from install root: `ls lib/ReSharperHost/linux-x64/dotnet >/dev/null && echo ok` → `ok`; `ls -d lib/ReSharperHost/*/ | grep -cE 'linux|macos|windows'` → 11. Honest caveat recorded: `Rider.Backend.sh` execs `"$D/runtime.sh"`, which does NOT exist in this Linux install (`ls *.sh` shows only Rider.Backend.sh + runtime-dotnet.sh) — treat the wrapper as vestigial/platform-materialized.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.check_index_coverage({ project: "jetbrains-rider", paths: ["lib/ReSharperHost/runtime-dotnet.sh", "lib/ReSharperHost/Rider.Backend.sh"] });
// both no_recorded_issue + metadata_match at generation_matches=true
```

## Verdict
Adopt the ladder shape (OS → libc discriminator → arch demotion → private-runtime dir → exec) for any dual-runtime product; adopt the quarantine-unblock step for macOS-shipped binaries. Adapt dir naming and error vocabulary. Omit Windows branches here (separate launchers own them). Cross-references: `launcher-script-contract` owns the JVM-side twin (JRE ladder + vmoptions filter); this capsule is its .NET counterpart. Coverage caveat: shell scripts are indexed best-effort; facts above read from source directly.

<!-- capsule-v2 -->
# Shell launcher platform-detection ladder — how does one install tree boot on six OS/arch combos?

**Source:** JetBrains dotMemory standalone install (pinned by self-hash `41e6f647…`; graph generation 2026-08-24T13:53:49Z); Codebase Memory `jetbrains-dotmemory`. **Question:** How does a single managed root serve every platform without managed-side platform branching at boot?

## dotMemoryUI / runtime-dotnet.sh detection prologue
**Path/Symbol:** `dotMemoryUI` (30 lines) and `runtime-dotnet.sh` (30 lines) — first 21 lines byte-identical (`diff <(head -21 a) <(head -21 b)` empty); exec targets differ (`$platformbin/dotMemory` vs `$dotnet/dotnet`).
**Signature:** POSIX sh; `case $(uname)` -> platform; `uname -m` + `getconf LONG_BIT` -> architecture; optional musl refinement.
**Data Shape:** platform ∈ {macos, linux-musl, linux}; arch ∈ {x64, arm64, arm}; RID stub dirs `<platform>-<architecture>/` hold launchers ONLY (linux ELF 73KB stripped PIE; macos Mach-O ~125KB; windows PE32+ console 460-468KB named dotMemory.exe).

### Decisive source
```sh
Linux) platform=$({ ldd --version 2>&1 || true; } | grep -q musl && echo linux-musl || echo linux)
    case $(uname -m) in
    x86_64)          architecture=x64;;
    aarch64)         architecture=$([ $(getconf LONG_BIT) -eq 32 ] && echo arm || echo arm64);;
    armv7l | armv8l) architecture=arm;;
    esac;;
root=$(cd "$(dirname "$0")"; pwd)
platformbin="$root/$platform-$architecture"
# Unblock files when downloaded in Safari
if [ "x$platform" = "xmacos" ] && xattr "$platformbin" | grep -q com.apple.quarantine; then
  xattr -d -r com.apple.quarantine "$platformbin"
fi
exec "$platformbin/dotMemory" "$@"
```

**Flow:** detect OS+arch -> resolve stub dir -> strip macOS quarantine xattr recursively -> exec the native launcher, which hands off to the shared managed root (linux-x64 additionally carries the private runtime, profiler natives, PdbServer).
**Invariant:** platform selection lives entirely in the SHELL prologue; the managed root stays RID-agnostic. The musl probe must run BEFORE choosing the dir or glibc/musl mismatch fails late and cryptically. DM_README.txt documents only './dotMemoryUI' as the entry.
**Probe:** `file windows-x64/dotMemory.exe linux-x64/dotMemory` → `PE32+ console x86-64` / `ELF 64-bit LSB pie executable … stripped`; prologue diff empty (both executed GREEN).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-dotmemory", query: "standalone avalonia shell boot host", limit: 5 });
```
Caveat: shell launchers are not symbol-indexed; decisive evidence is the direct script read.

## Verdict
Adopt the shell-side detection ladder (musl probe, LONG_BIT arm disambiguation, quarantine scrub) for any bundled-runtime tool; adapt dir naming to your RID scheme; omit the crossgen2/sos extras unless you also need AOT tooling beside your app.

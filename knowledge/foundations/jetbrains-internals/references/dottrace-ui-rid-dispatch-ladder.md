<!-- capsule-v2 -->
# RID dispatch ladder — how does one POSIX launcher resolve OS/libc/arch before any managed runtime loads?

**Source:** JetBrains dotTrace standalone distribution (proprietary distribution; study/reference use only, citations-only), pin `?@?` (not git-managed; identity = root + generation 2026-08-24T13:55:36Z); Codebase Memory `jetbrains-dottrace` (12,537 nodes, FULL mode). **Question:** How does a single entry script pick the right native bootstrapper across macOS/Linux, glibc/musl, x64/arm64/arm — and fail?

## Entry-script RID computation
**Path/Symbol:** `dotTraceUI` (install-root POSIX shell script, 950 bytes; the graph's lone Bash file).
**Signature:** `exec "$root/$platform-$architecture/dotTrace" "$@"`.
**Data Shape:** inputs = `uname`, `uname -m`, `ldd --version`, `getconf LONG_BIT`; output = one of `{macos,linux,linux-musl}-{x64,arm64,arm}` directory names; failures exit 1/2 loudly.

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
if [ "x$platform" = "xmacos" ] && xattr "$platformbin" | grep -q com.apple.quarantine; then
  xattr -d -r com.apple.quarantine "$platformbin"
fi
exec "$platformbin/dotTrace" "$@"
```

**Flow:** uname → platform family → libc flavor probe (musl via ldd banner) → machine → arch token (aarch64 demotes to `arm` when the userland is 32-bit per LONG_BIT) → optional macOS quarantine-xattr strip (Safari downloads) → exec native bootstrapper in the computed directory.
**Invariant:** the dispatch directory name equals the computed RID family; unsupported combinations fail LOUDLY (exit 1/2) instead of guessing — this install ships no `linux-musl-*` directories at all, so musl hosts fail at exec by design rather than silently running a glibc build.
**Probe:** deterministic: replicate the ladder on this host (`sh`: uname=Linux, ldd=glibc, x86_64) → resolves `linux-x64/dotTrace`, which exists and is ELF x86-64 (`file` confirms). Windows is intentionally absent from the script — `windows-x64/dotTrace.exe` is launched directly by the OS.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.check_index_coverage({ project: "jetbrains-dottrace", paths: ["dotTraceUI"] });
// → best-effort stored-artifact record (generation matches); the graph holds one Bash-language
//    file node for dotTraceUI (get_architecture languages: Bash 1), but bm25 ranks doc-XML above it,
//    so text search does not surface the script — direct read is the decisive evidence.
```

**Twin instance:** `dotnet-runtime-launcher-ladder` (Rider lane, source jetbrains-rider) carries the identical uname→musl-probe→LONG_BIT→quarantine grammar for an IDE-resident private .NET runtime; this capsule is the standalone-tool entry-point instance of the same pattern.

## Verdict
Adopt the compute-then-exec ladder: derive RID from environment probes, name directories exactly like the computed token, fail loudly on unknown combos, and sanitize macOS quarantine bits before exec. Adapt the RID vocabulary to your host set. Omit the specific bundled-runtime layout (linux-x64 carries a private `dotnet/`).

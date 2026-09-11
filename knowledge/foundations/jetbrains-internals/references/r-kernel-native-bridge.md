<!-- capsule-v2 -->
# R kernel native bridge — how do you drive an interpreted language whose runtime must live beside the interpreter, including on remote hosts?

**Source:** JetBrains DataSpell installed build `DS-261.26222.84`, `plugins/r-plugin` (R helper scripts GPL-2/3 "Rkernel … JetBrains s.r.o."; compiled parts proprietary). Codebase Memory `jetbrains-dataspell`. **Question:** What does the R plugin actually ship to make R executable, and what is the remote-host contract?

## Interpreter-native script kernel + per-arch ELF wrapper launchers
**Path/Symbol:** `plugins/r-plugin/R/init.R` (17,786-byte kernel init; `.jetbrains$getSysEnv` :351-361, `env$View` :504-505), `R/GetEnvVars.R:get_os` (:17-31), plus `extract_symbol.R`, `GetVersion.R`, `ram_size.R`, `render_markdown.R`, `package_summary.R`, `extraNamedArguments.R`, subdirs `interpreter/ packages/ projectGenerator/`; native launchers `rwrapper-x64-osx`, `rwrapper-arm64-linux`, … (ELF aarch64, dynamically linked, not stripped).
**Signature:** host side: `RInteropUtil.runRWrapper(...)`, `RRemoteHost.ensureRWrapperUploaded(...)` (class-name strings inside `r-plugin/lib/r-plugin.jar`; the module also depends on `intellij.libraries.grpc.netty.shaded`).
**Data Shape:** logic lives in R-language source executed BY the user's R (kernel init, env-var capture, symbol extraction for the editor); the only compiled pieces are thin per-arch launcher binaries and a gRPC bridge — so kernel behavior follows whatever R version the user owns.

### Decisive source
```r
# GetEnvVars.R:17-31 — OS ladder used by the kernel bootstrap
get_os <- function(){
  sysinf <- Sys.info()
  if (!is.null(sysinf)){
    os <- sysinf['sysname']
    if (os == 'Darwin') os <- "osx"
  } else { ## mystery machine
    os <- .Platform$OS.type
    if (grepl("^darwin", R.version$os)) os <- "osx"
    if (grepl("linux-gnu", R.version$os)) os <- "linux"
  }
  tolower(os)
}
```

**Flow:** IDE resolves the user's R → runs `init.R` through it (kernel state, `.jetbrains` helpers) → editor requests (symbols, package summaries, markdown render, RAM size) execute as small single-purpose R scripts → transport back to the IDE rides the shaded gRPC channel launched via the per-arch `rwrapper` binary → for REMOTE interpreters the host uploads the matching wrapper over SFTP (`ensureRWrapperUploaded`) before first use, because the remote arch/os may differ from the client.
**Invariant:** never assume the kernel binary matches the IDE platform — the wrapper matrix is per-arch-os AND must be re-provisioned per remote host; and never move kernel logic into JVM code that would pin an R version. The GPL header on the R sources vs proprietary jars is itself load-bearing provenance: the two planes are separately licensed and separately distributable.
**Probe:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-dataspell", query: "get_os sysinfo R kernel env vars", mode: "default", limit: 6 }); // rank-1: r-plugin.R.GetEnvVars.get_os :17-31
await mcp.codebase_memory.check_index_coverage({ project: "jetbrains-dataspell", paths: ["plugins/r-plugin/R/GetEnvVars.R","plugins/r-plugin/R/init.R"] }); // no_recorded_issue x2
// deterministic filesystem probe for the non-indexed plane:
await tools.bash({ command: "cd $REFERENCE_ROOT/dataspell/plugins && file r-plugin/rwrapper-arm64-linux | grep -o 'ELF 64-bit LSB executable.*aarch64' | head -c 40 && ls r-plugin/R/*.R | wc -l" }); // -> ELF…aarch64 + >=9 scripts
```

## Verdict
Adopt: ship language kernels as interpreter-native scripts + minimal per-arch launcher binaries; upload the launcher to remote hosts before attach; keep heavy semantics in the target language so users' own runtimes stay authoritative. Adapt the transport (gRPC here) and wrapper naming. Omit fsnotifier binaries (generic VFS machinery, owned by platform behavior, not the R seam).

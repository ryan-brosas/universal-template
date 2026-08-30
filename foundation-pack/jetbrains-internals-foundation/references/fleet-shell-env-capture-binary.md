<!-- capsule-v2 -->
# fleet-shell-env-capture-binary — how do you read the user's REAL login-shell environment without sourcing rc files yourself?

**Source:** JetBrains installed distributions (proprietary) air build `262.132.35`, pin `?@?`. Codebase Memory `jetbrains-air`. **Question:** What native primitive does Fleet use to obtain the interactive login shell's environment, and what is its failure contract?

## printenv shell-env — PTY-run interactive capture, JSON out
**Path/Symbol:** `lib/app/bin/printenv` (2,789,936 B; ELF static-PIE x86-64 stripped musl; embedded crate paths `fleet/native/crates/exec/src/{executor.rs,unix/reaper/*}`, `fleet/native/printenv/src/shell_env_command.rs`). **Signature:** `printenv shell-env` → JSON object of environment variables on stdout.
**Data Shape:** subcommands: `shell-env` ("prints shell environment variables, in json format, as it was run logged in and interactively"), `license`. No other flags beyond -h/-V.

### Decisive source
\`\`\`text
$ ./printenv --help          # executed against the shipped binary
Commands:
  shell-env  prints shell environment variables, in json format,
             as it was run logged in and interactively
  license    displays OSS licenses used in this binary
# failure-ladder strings embedded in the binary:
"shell executed successfully, adopting environment"
"failed to load env from shell, will fall back to std::env"
"shell execution timed out" · "Environment is empty"
"Uncorrect utf8 found when reading env. Skipping variable"
# mechanics visible in symbols/strings:
PtyOptions · SetPanic · Setsid · SignalChdir · Termios · close_stdin
"exec /usr/bin/env -0  > '"   # null-dump of captured env
fork/wait reaper over registered pids
\`\`\`

**Flow:** spawn a PTY → setsid + termios raw setup → exec the user's login shell INTERACTIVELY inside it (so profile/rc files run exactly as at the desk) → ask the shell to dump its environment NUL-separated via \`exec /usr/bin/env -0\` → parse to JSON, skipping non-UTF8 variables one-by-one → adopt; on any failure (timeout, empty env, exec miss) fall back to `std::env` of the calling process.
**Invariant:** capture must never mutate the user's shell config and must terminate: timeout is bounded, stdin closed, pids reaped via a registered-pid wait table. Non-UTF8 vars are skipped individually — one bad variable cannot fail the capture.
**Probe:** \`./printenv --help\` reproduces the two-command table verbatim; \`file lib/app/bin/printenv\` → static-pie linked (no runtime deps).
**Retrieve:** negative retrieval recorded (binary plane):
\`\`\`ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-air", query: "skiko", limit: 5 });
// → total: 0 ; same for "printenv shell-env"; coverage: lib/app/bin/printenv no_recorded_issue/not_tracked
\`\`\`

## Verdict
Adopt: capture login-shell env by RUNNING the user's real shell under a PTY and exporting \`env -0\` from inside it — never by parsing rc files; always ship the std::env fallback and per-variable UTF8 skip. Adapt the output channel (JSON here) and timeout values. Omit JetBrains' reaper/exec crate internals (upstream Rust). Relationship note: this is the NATIVE sibling of the descriptor-era `shell-env-promotion-force-vars` / `zdotdir-config-takeover-ladder` capsules — IDE products promote env INTO shells; Fleet's thin client harvests env FROM the shell at boot.

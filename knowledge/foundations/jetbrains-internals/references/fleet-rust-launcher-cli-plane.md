<!-- capsule-v2 -->
# fleet-rust-launcher-cli-plane — what replaces bin/*.sh when the whole boot chain is native?

**Source:** JetBrains installed distributions (proprietary) air build `262.132.35`, pin `?@?`. Codebase Memory `jetbrains-air`. **Question:** How does a Fleet-lineage install launch subsystems when it has NO shell launcher script (contrast: `launcher-script-contract`)?

## One static Rust CLI as the Ship launcher
**Path/Symbol:** `lib/app/bin/air` (6,599,568 B; ELF static-PIE x86-64, stripped, musl target per embedded bazel paths `x86_64-unknown-linux-musl-opt/bin/fleet/native/launcher/src/{main,workspace}.rs`; clap 4.5.58). **Signature:** `air [OPTIONS] [FORWARDED_FLEET_OPTIONS]... [COMMAND]`.
**Data Shape:** commands: `launch workspace` (boot a workspace), `dock {start|stop|endpoint|ships|ship_descriptor|quit}` (call the local daemon's dock API), `license`. Options: `-w/--wait`, `-c/--cache-path <dir>`, `--machine-readable-output` (JSON progress instead of bars). Positional tail after first arg or `--` is forwarded verbatim to the spawned Air.

### Decisive source
\`\`\`text
$ ./air --help          # executed against the shipped binary
Commands: launch | dock | license | help
Options: -w, --wait / -c, --cache-path <cache_path> /
         --machine-readable-output / -h/-V
$ ./air dock --help
Commands: start stop endpoint ships ship_descriptor quit
# internal grammar surfaced by strings:
LaunchShipRequest json argfile · -Dfleet.ship.autoUpdate=true|false ·
libc-implementation auto-detect (glibc/musl) · fsd/dock/jbr path overrides ·
workspace-version, jbr-version defaults · ship-id stop|secret|descriptor
\`\`\`

**Flow:** user runs `air [--wait] [-c cache]` → optional forwarded options passed to spawned Air → `launch workspace` resolves JBR/dock/fsd artifacts (path override else download; versions default via network call) → ship lifecycle managed through the local jetbrainsd daemon's API (`air dock ships|ship_descriptor|stop`) → `--machine-readable-output` switches the same flow to JSON lines for embedding.
**Invariant:** the launcher is position-independent STATIC (musl): zero runtime deps, safe to exec from any installer context; every artifact location is overridable so CI can pin offline copies; forwarding-after-first-arg keeps user flags out of the launcher grammar.
**Probe:** \`./air --help | sed -n '1,12p'\` reproduces the command table above; \`file lib/app/bin/air\` → static-pie linked, stripped.
**Retrieve:** negative retrieval recorded:
\`\`\`ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-air", query: "printenv shell-env", limit: 5 });
// → total: 0 (launcher binaries are extension-less not_tracked paths; coverage check: no_recorded_issue)
\`\`\`

## Verdict
Adopt: replace shell launchers with ONE static CLI exposing subcommands for each bootable subsystem plus a daemon-control verb group, JSON output mode for machine callers, and path/version overrides for offline determinism. Adapt command names and the LaunchShipRequest schema to your domain. Omit Fleet's artifact hosts and credential flows ("cannot read credentials, retrying" ladder is upstream-only). Contrast caveat: this REPLACES the JRE-ladder bash contract of `launcher-script-contract` — do not port both patterns to one product without deciding which layer owns boot.

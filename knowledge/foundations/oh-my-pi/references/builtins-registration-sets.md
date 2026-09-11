<!-- capsule-v2 -->
# Three-set builtin registration — which commands shadow real system binaries, and who decides?

**Source:** oh-my-pi (see pack SKILL.md Provenance) MIT `main@4854db85`; Codebase Memory `oh-my-pi`. **Question:** How are ~120 builtins partitioned so an embedding shell can install the non-shadowing set unconditionally but withhold destructive utilities?

## default_builtins / utility_builtins / process_builtins
**Path/Symbol:** `crates/pi-builtins/src/factory.rs:` `default_builtins(set: BuiltinSet)` (:25-182), `utility_builtins()` (:192-317), `process_builtins()` (:326-355); feature table `Cargo.toml` (`default = ["base", "utils"]`, one `util.<name>` feature per utility, `"builtin.kill" = ["util.procs"]`, `"util.base64" = ["util.base32"]`).
**Signature:** `fn default_builtins<SE>(set) -> HashMap<String, Registration<SE>>`; `fn utility_builtins/process_builtins<SE>() -> Vec<(&'static str, Registration<SE>)>`.
**Data Shape:** POSIX special builtins registered `.special()` (break : exit : trap : unset …); BashMode-only extras (echo, printf, mapfile+readarray aliasing ONE type, test + `[` alias, source as special dot, dirs/pushd/popd); unimplemented stubs `disown`/`logout` → `UnimplementedCommand`.

### Decisive source
```rust
/// These are kept out of [`default_builtins`] because they shadow real system
/// binaries: the embedding shell decides whether to install them (and may
/// withhold the destructive ones — `rm`, `mv`, `ln`).
pub fn utility_builtins<SE>() -> Vec<(&'static str, Registration<SE>)> { ... }

/// Kept separate from [`default_builtins`] because they shadow real system
/// binaries, and separate from [`utility_builtins`] because the embedding shell
/// installs them UNCONDITIONALLY — they exist so a long-lived embedded shell can
/// inspect and control its own children without forking.
pub fn process_builtins<SE>() -> ... { pgrep/pkill/pidwait/ps/top/sleep/timeout/nohup }
```

**Flow:** embedder calls `default_builtins(BuiltinSet::ShMode|BashMode)` for POSIX/bash core → optionally adds `utility_builtins()` (~60 file/text tools incl. rm/mv/ln) → adds `process_builtins()` always. `nohup` registers with `.transparent_background_wrapper()` so brush spawns the operand directly with session reparenting.
**Invariant:** The three sets are a security/behavioral boundary, not organization: shadowing utilities are OPT-IN per embedder; process tools are part of the shell's own job-control contract. One module = one command = one cargo feature; shared engines live behind their own features (`util.proc-match` behind pgrep/pkill/pidwait, `util.procs` behind kill).
**Probe:** deterministic anchors from repo root: `grep -c 'withhold the destructive ones' crates/pi-builtins/src/factory.rs` = 1; `grep -c 'transparent_background_wrapper' crates/pi-builtins/src/factory.rs` = 1.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "utility_builtins shadow destructive rm mv", limit: 10, fields: ["signature", "name", "file"] });
```
Live-resolved @4854db85: rank-2 `factory.utility_builtins factory.rs:192-317`; rank-1 hit is the pi-shell consumer that installs them.

## Verdict
Adopt the three-set split + per-command cargo features for any embedded tool suite. Adapt names to your host; keep destructive tools in a separately-installable vector. Omit brush-specific registration builders (`.special()`, decl vs raw-arg variants) beyond their semantic labels.

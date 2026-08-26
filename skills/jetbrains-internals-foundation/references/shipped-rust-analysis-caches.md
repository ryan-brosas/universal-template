<!-- capsule-v2 -->
# shipped-rust-analysis-caches — how does an offline IDE warm-start heavy analysis without a first-run download?

**Source:** JetBrains installed distributions (proprietary), RustRover decisive instance. **Question:** What must ship inside the plugin dir so code analysis works before any network/toolchain interaction?

## plugins/intellij-rust/caches/: version-pinned prebuilt analysis inputs
**Path/Symbol:** `rustrover/plugins/intellij-rust/caches/` → `rust-stdlib-vendor-1.97.1.zip`, `rust-src-bundle-1.97.1.zip`, `macro-expansion-cache-1.97.1.zip`, `crates-local-index.zip`.
**Signature:** `<artifact>-<toolchain-version>.zip` for stdlib vendor/src bundle/macro expansion; the crates index is UNVERSIONED (`crates-local-index.zip`) because it indexes the registry, not a toolchain.
**Data Shape:** four zips; three keyed to exactly `1.97.1` (the rustc version the plugin's analysis was built against); macro-expansion-cache = PRECOMPUTED expansion results (proc-macro output), stdlib-vendor + src-bundle = the standard library sources/vendored deps needed for name resolution and doc lookup.

### Decisive source
```
$ ls -la rustrover/plugins/intellij-rust/caches/
rust-stdlib-vendor-1.97.1.zip
macro-expansion-cache-1.97.1.zip
rust-src-bundle-1.97.1.zip
crates-local-index.zip
```

**Flow:** user opens a project with ANY local toolchain → plugin resolves the project's sysroot; when sources/expansions for the pinned version are needed, it serves the SHIPPED zips instead of downloading or invoking cargo → analysis, completion, and docs work offline from second zero; a mismatched toolchain falls back to computing locally (the caches are an accelerator, not the truth).
**Invariant:** cache artifacts are pinned to the PLUGIN build's expected toolchain (`-1.97.1` suffix) — never mix versions across plugin updates, and never treat the shipped caches as authoritative over a real sysroot. The unversioned crates index is registry-shaped data, refreshed on a different cadence than toolchain-keyed caches.
**Probe:** `bash -c 'ls rustrover/plugins/intellij-rust/caches/ | sort'` → the four zips above; `bash -c 'unzip -l rustrover/plugins/intellij-rust/caches/rust-src-bundle-1.97.1.zip | head -5'` shows library source roots inside.
**Retrieve:** binary artifacts are not symbol-indexed; coverage check:
```ts
await mcp.codebase_memory.check_index_coverage({ project: "jetbrains-rustrover", paths: ["plugins/intellij-rust/caches/rust-src-bundle-1.97.1.zip"] });
```

## Verdict
Adopt: ship toolchain-version-pinned prebuilt caches (sources + proc-macro expansions + registry index) inside the feature plugin to make heavy analysis functional offline at first boot. Adapt: pin-suffix scheme to your toolchain versioning; decide which of your analyses have precomputable outputs. Omit: Rust-specific stdlib layout. Caveat: contents inferred from names + zip listing; internal zip layout not exhaustively enumerated.

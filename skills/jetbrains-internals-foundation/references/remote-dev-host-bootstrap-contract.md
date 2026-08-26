<!-- capsule-v2 -->
# Remote-dev host bootstrap contract (launcher.sh) - what does it take to boot an IDE backend on an arbitrary glibc host with ZERO system expectations?

**Source:** PhpStorm installed build PS-262.9437.196 (plugins/remote-dev-server/bin/launcher.sh, 573L POSIX sh, set -e -u -f); Codebase Memory project jetbrains-phpstorm. **Question:** Port a self-contained remote-backend launcher: subcommand surface, config layout, JRE isolation, font fallbacks, and the generated-files contract.

## Five-parameter internal launcher + generated-contract files
**Path/Symbol:** launcher.sh:161-171 (five positionals from wrapper: script name, product code, product UC class, vmoptions basename, default Xmx), :197-215 (subcommand aliases run->remoteDevHost, warm-up->warmup, status->remoteDevStatus, invalidate-caches->invalidateCaches, stop->exit), :44-63 (registerBackendLocationForGateway symlink registry under HOME/.cache/JetBrains/RemoteDev/userProvidedDist with non-alnum-to-underscore naming, refused-if-exists), :114-146 (docker detection via /proc/1/cgroup grep docker|lxc plus .dockerenv/.dockerinit), :105-108 (WSL2 via kernel osrelease), :248-319 (legacy per-project vs new app-level config ladder; missing config dir = first launch = force New UI), :355-426 (musl/gcompat probes by INVOKING ld-linux and grepping stderr; JBR symlink-copy; every bin executable plus jexec/jspawnhelper wrapped by sh shims running ld-linux --library-path selfcontained/lib), :321-353 (fontconfig template sed PATH_FONTS/PATH_JBR into pid temp dir; FONTCONFIG_PATH prepend; XDG_DATA_DIRS augment; XDG_DATA_HOME untouched by comment), :428-470+504-541 (generated properties file exported as PRODUCT_UC+_PROPERTIES), :471-510 (generated vmoptions exported as PRODUCT_UC+_VM_OPTIONS), :88+:553-554 (cleanup trap EXIT INT HUP incl kill XVFB_PID; NO exec so trap survives - stated in comment).

### Decisive source
```sh
cat >"$file" <<EOT
#!/bin/sh
exec $LD_LINUX --library-path "$SELFCONTAINED_LIBS" "${file}.bin" $extra_arg "\$@"
EOT
# Hardcoded list copied from [org.jetbrains.intellij.build.impl.BundledRuntimeImpl.executableFilesPatterns]
printf '\nidea.required.plugins.id=com.jetbrains.remoteDevelopment' >> "$TEMP_REMOTE_DEV_PROPERTIES_PATH"
```

**Flow:** wrapper passes five params; direct invocation errors pointing at the wrapper. Generated properties encode POLICY as data: idea.config/plugins/system/log.path (legacy mode), tips disabled, shared-indexes auto-consent, required-plugin pin com.jetbrains.remoteDevelopment (backend cannot be disabled), ide.no.platform.update=true (version choice belongs to Gateway), eap.login.enabled=false, jdk.lang.Process.launchMechanism=vfork (CWM-5782), inter-font forced, idea.io.coarse.ts=true (IJPL-841), jdk.configure.existing=true default (REMOTE_DEV_JDK_DETECTION knob), Docker extras unknown.sdk.show.editor.actions=false + remotedev.run.in.docker=true (GTW-88). Generated vmoptions: product 64.vmoptions copied, Toolbox-style sibling IDE_HOME.vmoptions APPENDED when readable ELSE default Xmx sed-replaced to 2048m, java.home pinned at the temp JBR when self-contained, preferIPv4Stack on WSL2 unless REMOTE_DEV_SERVER_ALLOW_IPV6_ON_WSL2=true, user.home/user.name reasserted (GTW-7947). Env knobs documented in usage(): REMOTE_DEV_SERVER_TRACE (set -x), USE_SELF_CONTAINED_LIBS=0, TRUST_PROJECTS, NEW_UI_ENABLED, NON_INTERACTIVE (auto without tty; legacy CWM_ aliases honored), LEGACY_PER_PROJECT_CONFIGS=1.
**Invariant:** the host promise is 'glibc + XDG dirs only': musl/gcompat hosts detected by RUNNING the dynamic linker and reading its stderr flip self-contained libs OFF rather than failing; pid-scoped temp files make concurrent launches safe; cleanup trap owns ALL temp state including a possibly-spawned Xvfb; exec is forbidden because it would discard the trap.
**Probe:** sh -n launcher.sh green this run; file inventory of plugins/remote-dev-server taken via graph File-node query (launcher.sh + selfcontained/{X11/xkb rules,fontconfig/fonts.conf}); UTF-16/fontconfig artifacts listed parse_partial were read directly per index-status instruction.
**Coverage caveat:** remote-dev-server.sh wrapper itself lives in the jar-less bin dir? It is referenced but not symbol-indexed; its five-positional call shape is reconstructed from the launcher's own validation block (:167-171).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.query_graph({ project: "jetbrains-phpstorm", query: "MATCH (f:File) WHERE f.file_path STARTS WITH 'plugins/remote-dev-server' RETURN f.file_path ORDER BY path" });
```

## Verdict
Adopt generated-properties/vmoptions files as the config contract for headless IDE-class backends - policy becomes diffable text. Adapt product-code env names and property keys. Omit the symlink dist registry only if your gateway-equivalent tracks installs elsewhere.
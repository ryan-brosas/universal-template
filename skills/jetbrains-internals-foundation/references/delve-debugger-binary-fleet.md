<!-- capsule-v2 -->
# Delve debugger binary fleet — how does a JVM IDE ship a native target-side debugger for every runtime it may debug?

**Source:** JetBrains GoLand installed distribution (proprietary binaries; study/reference use only) `GO-262.9437.195`; Codebase Memory `jetbrains-goland`. **Question:** what targeting dimensions must a bundled native debugger cover before you can promise "attach anywhere"?

## Per-target-runtime fleet inside the language plugin
**Path/Symbol:** `plugins/go-plugin/lib/dlv/{linux,linuxmusl,linuxarm,linuxarmmusl,mac,macarm,windows,windowsarm}/dlv[.exe]` — 8 binaries, 13.7–22.9 MB each.
**Signature:** artifact census (directory layout IS the contract; no manifest declares it):
```
linux/ 16,118,880 B · linuxmusl/ 15,788,984 B · linuxarm/ 13,997,376 B · linuxarmmusl/ 13,728,728 B
mac/ 16,047,600 B · macarm/ 14,323,888 B · windows/dlv.exe 22,931,456 B · windowsarm/dlv.exe 14,230,528 B
```
**Data Shape:** os × arch × libc dimensions; musl variants exist ONLY for linux targets (Alpine-style static-linkage targets need their own build); windows uses .exe suffix + no exec bit; unix binaries carry +x.

### Decisive source
```text
$ strings -n 10 plugins/go-plugin/lib/dlv/linux/dlv | grep -m1 'go1.'
	go1.27rc1                      # delve built WITH a Go 1.27rc1 toolchain from
/mnt/agent/temp/buildTmp/go/src/vendor/golang.org/x/crypto/…   # JB build infra path
```

**Flow:** session picks target runtime (remote SSH/container/local) → launcher resolves `lib/dlv/<os>[musl][arm]/dlv` matching the TARGET, not the IDE host → delve runs where the program runs; JVM plugin jar stays untouched.
**Invariant:** the debugger is TARGET-side tooling: one fleet per supported target RUNTIME (libc dimension included), never a single host binary; binaries ride the language PLUGIN (not lib/) because only Go sessions need them; no descriptor/EP declares them — the layout itself is the lookup table. Coverage caveat: deeper version contract requires executing dlv (`dlv version`), intentionally not done in a mining lane.
**Probe:** `ls plugins/go-plugin/lib/dlv/ | tr '\n' ' '` → `linux linuxarm linuxarmmusl linuxmusl mac macarm windows windowsarm`; `find plugins/go-plugin/lib/dlv -type f | wc -l` → `8`.

## Get live surrounding code
**Retrieve:** (binary artifacts are ignored-suffix files — coverage metadata lists them as not_indexed_file)
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-goland", query: "delve debugger attach", limit: 5 });
await mcp.codebase_memory.check_index_coverage({ project: "jetbrains-goland", paths: ["plugins/go-plugin/lib/dlv/linux/dlv"] });
```

## Verdict
Adopt: ship per-target-runtime native tool fleets under a convention-path layout keyed os×arch×libc; treat layout-as-contract with a census probe. Adapt: dimensions to your targets (add musl-equivalents only where linkage actually diverges). Omit: executing or re-distributing the binaries; assume their absence from any symbol index.

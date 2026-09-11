<!-- capsule-v2 -->
# Engine reuse via embedded foreign IDE — how did CLion swap its C++ engine for Rider's (radler)?

**Source:** JetBrains IDE distributions (proprietary distribution; plugin.xml Apache-2.0-marked); study/reference use only; Codebase Memory `jetbrains-clion`. **Question:** How does a product replace its core language engine with ANOTHER product's backend, and which descriptor mechanisms make the host product's native engine incompatible?

## Connected graph-selected seam
**Path/Symbol:** `clion/plugins/clion-radler/lib/clion-radler.jar:META-INF/plugin.xml` + `lib/modules/` — 38 jars, 12+ named `intellij.rider.*` (rider.rdclient.dotnet, rider.cpp.core, rider.cpp.core.cmake, rider.cpp.injection, rider.cwm.core…).
**Signature:** `<incompatible-with>com.intellij.modules.appcode.ide</incompatible-with>` + `<incompatible-with>com.intellij.cidr.lang</incompatible-with>`; module gating `<module name="intellij.rider.rdclient.xml" required-if-available="intellij.platform.backend">`; OS pinning `<version>262.9437.136-linux-x86_64</version>`.
**Data Shape:** the plugin declares platform-module deps (`com.intellij.modules.os.linux`, `...arch.x86_64`), requires Native Build Tools, embeds its own icon library jar (`intellij.rider.icons.jar`: 5,197 entries under resharper/, expui/, rider/, DotMemory/DotTrace/DotCover namespaces) — the ENTIRE Rider UI asset plane rides inside CLion.

### Decisive source
```xml
<id>org.jetbrains.plugins.clion.radler</id>
<dependencies>
    <plugin id="com.intellij.modules.os.linux" />
    <plugin id="com.intellij.modules.arch.x86_64" />
```
```xml
<incompatible-with>com.intellij.cidr.lang</incompatible-with>
<module name="intellij.rider.rdclient.dotnet" required-if-available="intellij.platform.backend">
```

**Flow:** old CIDR C++ language modules are declared INCOMPATIBLE so they can never coexist → radler contributes rider.* modules providing the replacement engine over RD protocol (rdclient) → frontend/backend split modules activate only when the backend exists (`required-if-available`) → per-OS artifact naming keeps binaries separate.
**Invariant:** "replace" is expressed as incompatibility declarations, not removal — a porter must model engine swaps as mutual exclusion constraints, not patches. Icon namespaces (`resharper/*`, `DotCover`) prove whole-subsystem asset trees move with an engine.
**Probe:** `ls clion/plugins/clion-radler/lib/modules | grep -c rider` → 12+; `unzip -p plugins/clion-radler/lib/clion-radler.jar META-INF/plugin.xml | grep incompatible-with`.
**Coverage caveat:** manifest plane; direct extraction.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-clion", query: "rider rdclient cpp engine", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: incompatibility-declared engine replacement, required-if-available conditional modules, arch/OS-pinned plugin artifacts. Adapt to your host's plugin dependency solver. Omit RD protocol internals. Pass-1's dotmemory/dottrace omit-record stands; radler is the cross-product engine case those lacked.

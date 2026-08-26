<!-- capsule-v2 -->
# Distribution overlay assembly — how does a Maven build overlay produce a bootable distribution layout, and which defaults does the operator-facing entrypoint rely on?

**Source:** Nexus Repository EPL-1.0 `main@0a8a425d` (`nexus-base-overlay/pom.xml` + `overlay/etc/nexus-default.properties` + `bundle.xml`); Codebase Memory `nexus-public`. **Question:** How do default config, data dir skeleton, and launcher scripts get into the final artifact without forking the application code — the mechanism the railway-nexus3 deployment template mounts its env over?

## src/main/resources/overlay/** is copied OVER the assembled server tree: bin/ launchers, etc/nexus-default.properties (defaults), jetty xml set, fabric configs, sonatype-work skeleton with clean_cache marker
**Path/Symbol:** `public/common/assemblies/nexus-base-overlay/src/main/resources/overlay/` — `etc/nexus-default.properties` (:3-7: `application-port=8081`, `application-host=0.0.0.0`, `nexus-args=${jetty.etc}/jetty.xml,${jetty.etc}/jetty-http.xml,${jetty.etc}/jetty-requestlog.xml`, `nexus-context-path=/`), `bin/nexus`+`setenv` launchers, `etc/jetty/{jetty,jetty-http,jetty-https,jetty-https-fips,nexus-web,override-default-web}.xml`, `etc/fabric/{mybatis,ehcache}.xml`, `sonatype-work/nexus3/clean_cache`; assembly descriptor `src/main/assembly/bundle.xml`; overlay wiring `pom.xml`.
**Signature:** Maven Assembly + overlay ` <overlay>rsc:directory</overlay>` copy semantics — later wins, no merging of individual files.
**Data Shape:** properties file is read by `bin/nexus` → Karaf-era `nexus-args` interpolates jetty config list; `DO NOT EDIT - CUSTOMIZATIONS BELONG IN $data-dir/etc/nexus.properties` banner defines the precedence contract: data-dir overrides distribution defaults.

### Decisive source
```properties
## DO NOT EDIT - CUSTOMIZATIONS BELONG IN $data-dir/etc/nexus.properties
##
# Jetty section
application-port=8081
application-host=0.0.0.0
nexus-args=${jetty.etc}/jetty.xml,${jetty.etc}/jetty-http.xml,${jetty.etc}/jetty-requestlog.xml
nexus-context-path=/
```

**Flow:** reactor builds all components → base-overlay module copies `overlay/**` on top of the assembled dependency tree → bundle.xml packages result into distributable → at runtime `bin/nexus` composes JVM args from setenv, reads nexus-default.properties then `$data-dir/etc/nexus.properties` overrides → Jetty boots per nexus-args → ApplicationLauncher/SpringComponentScan take over (see two-phase-component-scan capsule) → sonatype-work skeleton (with clean_cache marker semantics) hosts blob store/task temp state.
**Invariant:** (1) Defaults file is NEVER edited in place — every operational knob is overridden in data-dir; deployments (like railway-nexus3-foundation's env gate) that write into the distribution instead of data-dir break on upgrade. (2) Overlay order is whole-file replacement: adding a jetty config means re-declaring nexus-args, not patching it. (3) The port/host/context-path trio here is what the healthcheck and reverse-proxy capsules assume.
**Probe:** deterministic anchors: `grep -c 'application-port=8081' public/common/assemblies/nexus-base-overlay/src/main/resources/overlay/etc/nexus-default.properties` = 1; `test -f public/common/assemblies/nexus-base-overlay/src/main/resources/overlay/bin/nexus && echo present` = present.
**Retrieve:** search_code project nexus-public pattern "nexus-default" — resolves the overlay properties Module node line-exact (doc/config-shaped paths).
**Verdict:** Adopt resource-overlay distribution assembly + defaults-vs-override precedence for self-contained server distributions. Adapt launcher scripts to your init system. Omit FIPS jetty variant unless shipping that compliance mode.

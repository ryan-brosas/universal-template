<!-- capsule-v2 -->
# Welcome-screen feature/fallback family — how do you degrade a capability surface gracefully when an optional technology plugin is absent?

**Source:** JetBrains GoLand installed distribution (proprietary; study/reference use only) `GO-262.9437.195`; Codebase Memory `jetbrains-goland`. **Question:** a start-surface lists per-technology features (Docker, Kubernetes, Terraform…); how does the surface stay complete when some host capabilities are missing?

## Real feature modules + fallback twins declared in a DIFFERENT module
**Path/Symbol:** `plugins/goland-customization-plugin/lib/goland-customization-plugin.jar!META-INF/plugin.xml` — content modules `intellij.go.welcomeScreen.{database,docker,kubernetes,terraform,terminal}` each declare `<welcomeScreenFeatureBackend id="X"/>` AND depend on that technology's plugin (`<plugin id="Docker"/>`, `org.intellij.plugins.hcl`, `org.jetbrains.plugins.terminal`, …); `intellij.go.ide` declares the fallback twins.
**Signature:** `<welcomeScreenFeatureBackend implementation="...GoWelcomeScreenFallbackDockerFeatureBackend" id="docker-fallback" order="after docker" />`.
**Data Shape:** ELEVEN declarations in one descriptor: 2 id-less ALWAYS-ON backends (HttpClient, Plugins — no id attribute), 5 real technology ids (database/docker/kubernetes/terraform/terminal, one per feature module gated by that tech's plugin dependency), 4 fallback twins (database-fallback/docker-fallback/kubernetes-fallback/terminal-fallback). Per-feature left-tab New-file actions add-to-group into `NonModalWelcomeScreen.LeftTabActions.New`; frontend/backend jar pairs ride beside (`intellij.platform.ide.nonModalWelcomeScreen.{frontend,backend}.jar`, featuresTrainer ×3).

### Decisive source
```xml
<!-- intellij.go.welcomeScreen.docker CDATA: loads ONLY when Docker plugin exists -->
<idea-plugin>
  <dependencies><plugin id="Docker" /><module name="intellij.go.ide" />…</dependencies>
  <extensions defaultExtensionNs="com.intellij.platform.ide">
    <welcomeScreenFeatureBackend implementation="com.intellij.go.welcomeScreen.docker.GoDockerFeatureBackend" id="docker" />
  </extensions>
</idea-plugin>
<!-- intellij.go.ide CDATA: fallback lives HERE, not in the feature module -->
<welcomeScreenFeatureBackend implementation="…GoWelcomeScreenFallbackDockerFeatureBackend" id="docker-fallback" order="after docker" />
<welcomeScreenFeatureBackend implementation="…GoWelcomeScreenFallbackKubernetesFeatureBackend" id="kubernetes-fallback" order="after kubernetes" />
```

**Flow:** optional tech present → both backends registered; real one sorts after-anchor first (order="after docker") and serves rich actions → tech absent → feature module never loads (unsatisfied plugin dependency) → fallback twin alone renders a degraded card pointing at install/config → surface stays structurally identical either way.
**Invariant:** degradation is expressed as id-family + order pairing ACROSS two modules — the fallback must NOT live in the module that disappears; ids are the join key (`docker` vs `docker-fallback`), order anchors place real before fallback deterministically; ABSENCE of an id means the backend is unconditional (always-on core features never degrade, so they never need a twin). This is the declarative counterpart of optional-depends fragments: same silent-skip semantics, positive UX contract added.
**Probe:** `unzip -p plugins/goland-customization-plugin/lib/goland-customization-plugin.jar META-INF/plugin.xml | grep -c 'id="[a-z]*-fallback"'` → `4`; `unzip -p … META-INF/plugin.xml | grep -c '<welcomeScreenFeatureBackend'` → `11` (2 id-less always-on + 5 real ids + 4 fallbacks; executed byte-exact 2026-08-25 — first draft expected 9 before the id-less pair was enumerated).

## Get live surrounding code
**Retrieve:** (zero-symbol expectation; coverage check recorded)
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-goland", query: "welcomeScreenFeatureBackend fallback", limit: 5 });
await mcp.codebase_memory.check_index_coverage({ project: "jetbrains-goland", paths: ["plugins/goland-customization-plugin/lib/goland-customization-plugin.jar"] });
```

## Verdict
Adopt: capability cards as (real backend gated by host-plugin dependency) + (fallback twin anchored after the real id, declared where it cannot vanish). Adapt: feature set and anchor vocabulary. Omit: Compose/Jewel rendering internals.

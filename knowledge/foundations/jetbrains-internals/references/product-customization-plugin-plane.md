<!-- capsule-v2 -->
# product-customization-plugin-plane — where does a product hide its branding/monetization overrides so the platform stays neutral?

**Source:** JetBrains installed distributions (proprietary), RustRover decisive instance. **Question:** How does a per-product customization layer override platform services and inject product-only UX without forking platform code?

## com.intellij.rustrover.customization: implementation-detail plugin with overrides="true" service swaps
**Path/Symbol:** `rustrover/plugins/rustrover-customization-plugin/lib/rustrover-customization-plugin.jar:META-INF/plugin.xml` → root `<idea-plugin implementation-detail="true">`, `<id>com.intellij.rustrover.customization</id>`, `<depends>com.intellij.modules.platform</depends>` only; content modules `intellij.rustrover.customization` (loading="required"), `.backend` (required-if-available="intellij.platform.backend"), `intellij.platform.trialPromotion.idesWithoutFreeTier`.
**Signature:** override idiom = `<applicationService serviceInterface="<platform SPI>" serviceImplementation="<product impl>" overrides="true" />`; product impls: `RustRoverExternalResourceUrls` (ExternalProductResourceUrls — where the IDE fetches product resources), `RustRoverWhatsNewInVisionContentProvider` (WhatsNewInVisionContentProvider).
**Data Shape:** three payload kinds in one tiny plugin: (1) service overrides via EP re-declaration with overrides="true"; (2) additive registrations (`defaultToolWindowLayout` with order="last", customScopesProvider TestScopeProvider); (3) monetization module `intellij.platform.trialPromotion.idesWithoutFreeTier` (TrialStatusBarWidget, StartTrialNotificationAction, PluginWithFreeTierEditorNotificationProvider, TrialAvailabilityCollector classes seen in the jar) — shipped ONLY by IDEs without a free tier.

### Decisive source
```xml
<idea-plugin implementation-detail="true">
  <id>com.intellij.rustrover.customization</id>
  <name>RustRover Customization</name>
  <content namespace="jetbrains">
    <module name="intellij.rustrover.customization" loading="required"><![CDATA[<idea-plugin>
      <extensions defaultExtensionNs="com.intellij">
        <applicationService serviceInterface="com.intellij.platform.ide.customization.ExternalProductResourceUrls"
                            serviceImplementation="...RustRoverExternalResourceUrls" overrides="true" />
        <defaultToolWindowLayout implementation="...RustRoverDefaultToolWindowLayoutExtension" order="last" />
      </extensions>]]></module>
    <module name="intellij.rustrover.customization.backend" required-if-available="intellij.platform.backend">…
        <applicationService serviceInterface="com.intellij.platform.whatsNew.WhatsNewInVisionContentProvider"
                            serviceImplementation="...RustRoverWhatsNewInVisionContentProvider" overrides="true" />…</module>
```

**Flow:** platform boots with a default ExternalProductResourceUrls → customization plugin loads last-ish (platform module dep only) → overrides="true" replaces the service instance → every "open product resources / what's new" lookup now hits RustRover's implementation → trial-promotion module registers its status-bar widget + notifications because this persona lacks a free tier.
**Invariant:** the customization plugin depends on NOTHING product-specific (`com.intellij.modules.platform`) and carries no language code — it is pure persona deltas; `implementation-detail="true"` marks it as infra so it stays out of user-facing plugin UI. Overriding is declared at the SAME extension point, not via a separate override registry.
**Probe:** `python3 -c "import zipfile;x=zipfile.ZipFile('rustrover/plugins/rustrover-customization-plugin/lib/rustrover-customization-plugin.jar').read('META-INF/plugin.xml').decode();print(x.count('overrides=\"true\"'), 'implementation-detail' in x, 'trialPromotion.idesWithoutFreeTier' in x)"` → `2 True True`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-rustrover", file_pattern: "plugins/rustrover-customization-plugin/**", query: "trial promotion widget", limit: 5 });
```
(jar XML/class list read directly; graph holds the plugin dir surface.)

## Verdict
Adopt: ship product personality as an implementation-detail plugin whose modules swap named platform SPIs with overrides="true" and append layout/order="last" defaults; gate backend-twin halves on platform module presence. Adapt: which SPIs your platform exposes as overridable. Omit: JetBrains trial/freetier business logic specifics. Caveat: single-install evidence (RustRover); other products presumably mirror the pattern with their own ids.

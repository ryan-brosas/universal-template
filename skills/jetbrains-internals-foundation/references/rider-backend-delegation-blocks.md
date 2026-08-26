<!-- capsule-v2 -->
# Rider backend-delegation per-language block — how does a thin-frontend language module wire editor seams to a backend process?

**Source:** JetBrains IDE installed build `Rider 262.8665.400` (`plugins/rider-unity/lib/modules/intellij.rider.plugins.unity.backend.jar:intellij.rider.plugins.unity.backend.xml:96-186`); Codebase Memory `jetbrains-rider`. **Question:** When the JVM side of an IDE is a thin frontend and real analysis happens in a non-JVM backend, what does its manifest contribute per language, and which registrations repeat verbatim for every language?

## The ShaderLab block as the decisive instance
**Path/Symbol:** `intellij.rider.plugins.unity.backend.xml` (404 lines whole) — ShaderLab region :96-115, JSON-derived types :117-137, UnityYaml :140-146, UXML :148-163.
**Signature:** per language L: `<fileType name="L" .../>` + `<rd.languageAssociation backendLanguage="B" frontendLanguage="F"/>` + the SAME seam set re-pointed at delegation handlers — `<lang.altEnter language="L" implementationClass=...ReSharperAltEnterMenuModelFactory/>`, `<backend.markup.adapterFactory language="L" .../>`, `<backend.actions.support language="L" .../>`, `<completion.contributor language="L" ...ProtocolCompletionContributor/>`, `<lang.documentationProvider language="L" ...FrontendDocumentationProvider/>`.
**Data Shape:** counts in this one file: `rd.solutionExtListener` ×9 (all `endpoint="IDE Frontend"`), `backend.markup.adapterFactory` ×4 (ShaderLab/JSON/UnityYaml/UXML), `backend.actions.support` ×5, `ProtocolCompletionContributor` ×3, `rd.languageAssociation` ×2. The `rd.*` namespace is Rider's protocol plane; `rdclient.*`/`rider.*` EPs are its extension surface.

### Decisive source
```xml
<fileType name="ShaderLab" fieldName="INSTANCE" implementationClass="...ShaderLabFileType" language="ShaderLab" extensions="shader"/>
<rd.languageAssociation backendLanguage="SHADERLAB" frontendLanguage="ShaderLab" />
<lang.altEnter language="ShaderLab" implementationClass="com.jetbrains.rider.intentions.altEnter.ReSharperAltEnterMenuModelFactory" />
<backend.markup.adapterFactory language="ShaderLab" implementationClass="com.jetbrains.rdclient.daemon.FrontendMarkupAdapterFactory" />
<backend.actions.support language="ShaderLab" implementationClass="com.jetbrains.rider.actions.RiderActionSupportPolicy" />
<completion.contributor language="ShaderLab" implementationClass="com.jetbrains.rider.completion.ProtocolCompletionContributor" />
```
(plus `<fileType name="HLSL" extensions="cg;cginc;hlslinc;compute;urtshader"/>` — an existing type EXTENDED with extensions only, no impl class: same reuse contract filetype-registration-contract owns.)

**Flow:** frontend parses/lexes locally (fileType + parserDefinition) → every semantic seam (completion, docs, quick-fixes, markup) delegates through Protocol* / Frontend* handlers over the RD protocol → `rd.solutionExtListener` pairs bind lifecycle listeners to named protocol endpoints so backend state changes drive UI → `rd.languageAssociation` tells the pair-mapping which backend language token equals the frontend one.
**Invariant:** the seam LIST is platform-generic but the implementations must be the delegation pair (Protocol/Frontend classes); registering a local analyzer where a delegation handler belongs silently forks behavior between monolith and split modes. Wrong port: copying only the fileType+parser lines and expecting highlighting to work — without `rd.languageAssociation` the backend's annotations never map onto frontend files.
**Probe:** deterministic jar read: `unzip -p plugins/rider-unity/lib/modules/intellij.rider.plugins.unity.backend.jar intellij.rider.plugins.unity.backend.xml | grep -c 'rd.solutionExtListener'` → 9; `grep -c 'backend.markup.adapterFactory'` → 4; `grep -c 'ProtocolCompletionContributor'` → 3.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-rider", query: "UnityPausepoint UnityExplorer rider-unity dotnet", limit: 10, fields: ["signature", "name", "file"] });
```
(verified live: graph resolves `jetbrains-rider.plugins.rider-unity.dotnet.JetBrains.ReSharper.Plugins.Unity.Rider` and `.dotnetDebuggerWorker` nodes plus the loose XML doc `plugins/rider-unity/dotnet/JetBrains.ReSharper.Plugins.Unity.xml` [1,564 lines, `no_recorded_issue` coverage] — the .NET-side contract mirror of this manifest.)

## Verdict
Adopt the per-language delegation-block shape (local syntax + remote semantics via a fixed handler pair + explicit language association) for any thin-client/backend IDE; adapt the RD protocol specifics to your transport; omit ReSharper/Rider protocol internals. Cross-references: pass-2's `frontend-split-product-modules` covers WHICH plugins ship thin; this capsule covers HOW each thin plugin's language modules register. Coverage caveat: jar-resident XML read by unzip (`not_tracked` freshness); companion .NET XML doc verified `no_recorded_issue`.

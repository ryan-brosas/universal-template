<!-- capsule-v2 -->
# ExternalAnnotations doc-id injection grammar — how do you attach behavior contracts to assemblies you cannot rebuild?

**Source:** JetBrains dotTrace standalone distribution (proprietary distribution; study/reference use only, citations-only), pin `?@?` (not git-managed; identity = root + generation 2026-08-24T13:55:36Z); Codebase Memory `jetbrains-dottrace` (12,537 nodes, FULL mode). **Question:** What is the exact file/member grammar that injects JetBrains.Annotations behavior attributes over unmodifiable third-party assemblies, and which variant is machine-generated?

## Per-member attribute injection over a doc-id key
**Path/Symbol:** `ExternalAnnotations/Microsoft/Microsoft.AspNetCore.Mvc.TagHelpers/Attributes.xml`: root `<assembly>`, per-member `<member>` + `<attribute ctor>` (whole file, 35 lines); generated twin form in `ExternalAnnotations/.NETFramework/System.ServiceModel.Activation/4.0.0.0.Nullness.Gen.xml:190-203`.
**Signature:** `<member name="P|M|F|T:<Namespace.Type.Member>">` → child `<attribute ctor="M:JetBrains.Annotations.XxxAttribute.#ctor" />`; generated nullness variant nests `<parameter name="p"> <attribute ctor="M:JetBrains.Annotations.NotNullAttribute.#ctor" /> </parameter>` and may annotate the method member itself (`CanBeNull`) as the return contract.
**Data Shape:** one XML file per annotated assembly, keyed by simple assembly name in the root element; directory taxonomy = framework family first (`.NETFramework`, `.NETStandard`, `WinRT`, `Unity`, `Microsoft`, `Misc`, plus legacy Silverlight/Catel dirs), then assembly name; file name suffix `.Gen` marks machine-generated nullness sets.

### Decisive source
```xml
<assembly name="Microsoft.AspNetCore.Mvc.TagHelpers">
  <member name="P:Microsoft.AspNetCore.Mvc.TagHelpers.AnchorTagHelper.Action">
    <attribute ctor="M:JetBrains.Annotations.AspMvcActionAttribute.#ctor" />
  </member>
</assembly>
```
```xml
<!-- .Nullness.Gen.xml generated variant -->
<member name="M:System.ServiceModel.ServiceHostingEnvironment.IsConfigurationBasedService(System.Web.HttpApplication,System.String@)">
  <parameter name="application">
    <attribute ctor="M:JetBrains.Annotations.NotNullAttribute.#ctor" />
  </parameter>
</member>
```

**Flow:** analysis opens an external assembly → looks up `ExternalAnnotations/<family>/<assembly>.xml` by root `assembly name=` match → for each member doc-id it synthesizes the listed attribute ctor applications in memory → the analyzer treats e.g. an MVC string property as ASP.NET MVC action-name context without the assembly ever being modified.
**Invariant:** the member key is a documentation id (`P:`/`M:`/`F:`/`T:` prefix), NOT reflection syntax — parameter types appear as back-tick/bracket doc forms; injection is additive-only and never rewrites the target; hand-written and `.Gen` files coexist under one schema so generators can regenerate their slice safely.
**Probe:** deterministic content assertions on the shipped corpus: the TagHelpers sample contains exactly 11 `<member name="P:…">` entries each carrying exactly one `AspMvc*Attribute.#ctor` injection; the Nullness.Gen sample carries nested `<parameter>` elements (lines verified directly, recorded in verification.md).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-dottrace",
  query: "ExternalAnnotations assembly member attribute ctor injection", limit: 10 });
// → 1,990 total hits across ExternalAnnotations/*.xml attribute nodes
//   (verified live); graph nodes resolve at file/member granularity — read the cited
//   XML ranges directly for byte-level grammar.
```

## Verdict
Adopt the pattern: external behavior-contract catalogs keyed by documentation ids, applied at analysis time over immutable dependencies — ideal for annotating third-party APIs your tool cannot rebuild. Adapt the attribute vocabulary to your own annotation set and the family taxonomy to your ecosystem. Omit shipping the entire upstream corpus wholesale (dotTrace carries ReSharper's full 76M corpus including Silverlight-era dirs — product-curated tools should prune).

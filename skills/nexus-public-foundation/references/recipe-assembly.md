<!-- capsule-v2 -->
# Recipe assembly — what is the plugin contract that turns (format × type) into a working repository with facets and a router?

**Source:** Nexus Repository EPL-1.0 `main@0a8a425d` (`formats/nexus-repository-raw/.../recipe/RawHostedRecipe.java`); Codebase Memory `nexus-public`. **Question:** How does a format plugin declare a repository flavor so the core can instantiate, configure, and route it — without core knowing the format?

## Recipe = @Qualifier-named component wiring facet providers + Router.Builder
**Path/Symbol:** `public/common/components/formats/nexus-repository-raw/src/main/java/org/sonatype/nexus/content/raw/internal/recipe/RawHostedRecipe.java:apply` (:58–65), `configure` (:70–101).
**Signature:** `class RawHostedRecipe extends RawRecipeSupport`; `@Component @Qualifier("raw-hosted")`; ctor takes `@Qualifier(HostedType.NAME) Type type, @Qualifier(RawFormat.NAME) Format format`; contract method `void apply(@Nonnull final Repository repository)`.
**Data Shape:** recipe support base supplies shared handler fields (`timingHandler`, `securityHandler`, `exceptionHandler`, `handlerContributor`, `conditionalRequestHandler`, `partialFetchHandler`, `contentHeadersHandler`, `lastDownloadedHandler`, `contentHandler`) as prototype-scoped providers; `PATH_MATCHER` constant covers the content space.

### Decisive source
```java
@Override
public void apply(@Nonnull final Repository repository) throws Exception {
  repository.attach(securityFacet.get());
  repository.attach(configure(viewFacet.get()));
  repository.attach(contentFacet.get());
  repository.attach(maintenanceFacet.get());
  repository.attach(searchFacet.get());
  repository.attach(browseFacet.get());
}

private ViewFacet configure(final ConfigurableViewFacet facet) {
  Router.Builder builder = new Router.Builder();
  // GET / forwards to /index.html — extra handlers intentionally omitted on this route
  builder.route(new Route.Builder()
      .matcher(and(new ActionMatcher(HttpMethods.GET), new SuffixMatcher("/")))
      .handler(timingHandler)
      .handler(indexHtmlForwardHandler)
      .create());

  builder.route(new Route.Builder()
      .matcher(PATH_MATCHER)
      .handler(timingHandler)
      .handler(contentDispositionHandler)
      .handler(securityHandler)          // authorize-once seam
      .handler(exceptionHandler)         // status mapping
      .handler(handlerContributor)       // PLUGIN INJECTION POINT
      .handler(conditionalRequestHandler)
      .handler(partialFetchHandler)
      .handler(contentHeadersHandler)
      .handler(lastDownloadedHandler)
      .handler(contentHandler)
      .create());

  builder.defaultHandlers(HttpHandlers.badRequest());
  facet.configure(builder.create());
  return facet;
}
```

**Flow:** at repository-creation time the core looks up the recipe by its `format-type` qualifier, then calls `apply(repository)`; the recipe attaches its facet set (each a lazily-provided prototype) and configures the ViewFacet's router. Handler order encodes the pipeline contract: timing → format-specific → security → exception → CONTRIBUTOR → conditional → partial-fetch → headers → last-downloaded → content. Default route returns 400.
**Invariant:** the contributor slot is MANDATORY in every recipe route or plugins silently lose their injection point. Routes are declarative per recipe; nothing mutates them later (runtime extension happens only via HandlerContributor). Format logic lives in facets; the recipe is pure assembly — this separation is why 20+ formats share one core.
**Probe:** `formats/nexus-repository-raw/src/test/java/org/sonatype/nexus/content/raw/internal/recipe/RawRecipeTestSupport.java` + `RawHostedRecipeTest.java` pin facet attach + route shapes for the raw family.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nexus-public", query: "RawHostedRecipe apply ConfigurableViewFacet Router.Builder handlerContributor", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt recipe-as-declarative-assembly with qualifier naming (format × type), facet attachment order, and the fixed handler skeleton including one contributor slot. Adapt Spring qualifiers and your facet lifecycle. Omit raw-specific handlers (contentDisposition/indexHtml forward) unless porting a file-serving surface.

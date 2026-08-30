<!-- capsule-v2 -->
# Shared utility distribution — how do many components consume ONE copy of utility code without vendoring drift?

**Source:** nodebestpractices CC-BY-SA-4.0 `master@dc3d60c29d54`; Codebase Memory `nodebestpractices`. **Question:** When multiple components on different servers need the same utilities, how do you keep exactly one copy deployable and replaceable?

## Wrap 3rd-party utilities behind your own module; publish as a PRIVATE npm package
**Path/Symbol:** `sections/projectstructre/wraputilities.md` (:1 title; :5-7 One Paragraph Explainer — the whole contract; :11-12 sharing-across-components header). Companion structure contracts: `components-and-3-tiers`, `dependency-lock-exact-chain`.
**Signature:** `ownFacade(thirdPartyUtil)` → publish(private) → consumers import via standard package.json dependency management. Distribution options named upstream: private modules (npm), private registry (npm Enterprise/Nexus-class), local npm packages (file: links).
**Data Shape:** one versioned package artifact, N consumer components; the facade — not the consumers — owns the dependency edge on the 3rd-party library.

### Decisive source
```text
# wraputilities.md :7 — the full contract in one paragraph
Once you start growing and have different components on different servers which consumes similar
utilities, you should start managing the dependencies - how can you keep 1 copy of your utility
code and let multiple consumer components use and deploy it? well, there is a tool for that, it's
called npm... Start by wrapping 3rd party utility packages with your own code to make it easily
replaceable in the future and publish your own code as private npm package. Now, all your code
base can import that code and benefit free dependency management tool.
```

**Flow:** components multiply and land on different servers → the same utilities are needed everywhere → copy-paste would fork behavior → wrap each 3rd-party utility behind your own thin module → publish your module as a PRIVATE package (private modules / private registry / local packages) → every component imports it like any other dependency and deploys with the normal pipeline.
**Invariant:** exactly ONE copy of the utility logic exists; replacing the underlying 3rd-party library is a change in ONE place (the facade) with zero consumer edits. Consumers never import the 3rd-party package directly — that would reintroduce the drift the facade exists to kill.
**Probe:** no upstream runner exists (docs-only repo). Deterministic probe, executed green at pin: `grep -c 'wrapping 3rd party utility packages' sections/projectstructre/wraputilities.md` = 1 && `grep -c 'private registry' sections/projectstructre/wraputilities.md` = 1 && `grep -c 'local npm packages' sections/projectstructre/wraputilities.md` = 1.

## Get live surrounding code
**Retrieve:** doc-shaped-graph note — BM25 `search_graph` returns ZERO tokens here; `search_code` with a decisive needle resolves the pinned file uniquely. Executed live:
```ts
await mcp.codebase_memory.search_code({ project: "nodebestpractices", pattern: "wrapping 3rd party utility packages", limit: 5 });
// => exactly 1 result: sections/projectstructre/wraputilities.md Module 1-14, matches "7"; total_results: 1
```

## Verdict
Adopt facade-wrapping plus private publishing as the default shared-utility mechanism once ≥2 deployed components need the same helper; treat `libraries/`-style folders (see `components-and-3-tiers`) as the packaging seed. Adapt the distribution channel to your infrastructure (modern equivalents: scoped private registries, internal mirrors). Omit the upstream tutorial links as normative and the local-file-package option for multi-server fleets (it does not travel across machines).

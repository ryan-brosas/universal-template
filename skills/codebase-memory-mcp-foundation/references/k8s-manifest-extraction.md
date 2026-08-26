<!-- capsule-v2 -->
# K8s manifest extraction — how do you turn YAML deployment files into graph nodes without a real k8s parser?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** How are Kustomize resources and K8s manifests mapped to definitions/imports with minimal grammar support?

## Key-scoped Kustomize walk + apiVersion/kind/name triple
**Path/Symbol:** `internal/cbm/extract_k8s.c` (header contract 1–12) + tests/test_pipeline.c:8993–9050.
**Signature:** extraction pass over CBM_LANG_KUSTOMIZE / CBM_LANG_K8S files.
**Data Shape:** KUSTOMIZE: top-level `block_mapping_pair` whose key ∈ {resources, bases, patches, components, patchesStrategicMerge} → one CBMImport per block_sequence item. K8S: first document's block_mapping yields apiVersion+kind+metadata.name → one CBMDefinition label "Resource", name "Kind/metadata-name".

### Decisive source
```c
// For CBM_LANG_KUSTOMIZE: walks top-level block_mapping_pair nodes whose key
// matches "resources", "bases", ... then emits one CBMImport per
// block_sequence item.
//
// For CBM_LANG_K8S: finds apiVersion, kind, and metadata.name scalars in the
// first document's block_mapping and emits one CBMDefinition ...
TEST(k8s_extract_kustomize) {
    ... ASSERT_GTE(r->imports.count, 2);
    ... strcmp(r->imports.items[i].module_path, "deployment.yaml") == 0) found_deploy = true;
```

**Flow:** language detection routes yaml-ish files with kustomize/k8s markers → grammar walk restricted to the FIRST document's top-level mapping → emit defs/imports → pass_k8s later links Resource nodes to code via name heuristics.
**Invariant:** First-document-only scoping avoids cross-document contamination; unknown keys are ignored rather than guessed.
**Probe:** `tests/test_pipeline.c:k8s_extract_kustomize`, `k8s_extract_manifest`, plus `infra_is_k8s_manifest` classification.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_extract_k8s", limit: 5 });
```

## Verdict
Adopt key-allowlisted minimal mapping for infra manifests; adapt the key set; omit Helm templating entirely rather than approximating.

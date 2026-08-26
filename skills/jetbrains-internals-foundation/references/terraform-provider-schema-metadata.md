<!-- capsule-v2 -->
# Terraform provider schema metadata — how is a declarative IaC language's provider catalog shipped as JSON schema?

**Source:** JetBrains IDE distributions (proprietary distribution; metadata JSON Apache-2.0/MIT); study/reference use only; Codebase Memory `jetbrains-goland`. **Question:** How does an IDE ship completion/validation for an entire declarative tool ecosystem as static JSON provider schemas, and what is the schema-version contract?

## Connected graph-selected seam
**Path/Symbol:** `goland/plugins/terraform/lib/terraform-metadata.jar:terraform/model/**` — 1,301 model files + 2 model-external; `terraform/model/provisioners/chef.json` etc.
**Signature:** per-resource JSON with `".schema_version":"2"`, `".sdk_type":"builtin"`, `name`, `type` (provisioner/data/resource), `version`, and a `schema` map.
**Data Shape:** `schema` attributes: `{"attributes_json":{"Type":"String","Optional":true}, "channel":{"Type":"String","Optional":true,"Default":{"Type":"string","Value":"stable"}}, "client_options":{"Type":"List","Optional":true,"ConfigImplicitMode":"Attr","Elem":{"Type":"SchemaElements","ElementsType":"String"}}}` — a faithful mirror of Terraform's own provider schema (Type/Optional/Default/Elem/ConfigImplicitMode).

### Decisive source
```json
{".schema_version":"2",".sdk_type":"builtin","name":"chef","type":"provisioner",
 "version":"v0.13.0-beta3",
 "schema":{"channel":{"Type":"String","Optional":true,
   "Default":{"Type":"string","Value":"stable"}},
   "client_options":{"Type":"List","Optional":true,"ConfigImplicitMode":"Attr",
     "Elem":{"Type":"SchemaElements","ElementsType":"String"}}}}
```

**Flow:** terraform plugin loads the metadata jar → each model file describes one provider resource/provisioner → completion proposes block attributes from `schema`, validation checks Type/Optional/Default → `".sdk_type":"builtin"` distinguishes first-party from third-party providers.
**Invariant:** the JSON is a lossless mirror of Terraform's runtime schema (same Type/Optional/Default/Elem vocabulary) so the IDE can validate WITHOUT running terraform. `.schema_version` must be respected — a porter who ignores it mis-parses newer files.
**Probe:** `unzip -p plugins/terraform/lib/terraform-metadata.jar terraform/model/provisioners/chef.json | python3 -m json.tool | head -8`; `unzip -l … | awk '{print $4}' | grep -c '^terraform/model/'` → 1301.
**Coverage caveat:** resource plane, direct extraction.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-goland", query: "terraform provider schema", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: ship a declarative tool's provider catalog as versioned JSON mirroring its runtime schema; validate offline against it; use `.sdk_type` to mark provenance. Adapt to your IaC host. Omit the Terraform corpus. This is the declarative-IaC twin of the terminal-command-spec plane — same "data mirrors an external tool's contract" pattern.

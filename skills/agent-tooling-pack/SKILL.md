---
name: agent-tooling-pack
description: "Use when creating or troubleshooting Pi packages/providers, configuring Fabric execution or models, selecting agent runners, or explicitly requesting Veda planning, implementation or review. Ordinary planning uses engineering-pack; Oracle consultation uses research-pack."
invocation: entry
---

# Agent tooling pack

These are optional tool-specific procedures, not the default engineering workflow.
Read only the matching procedure. Resolve its helpers and references relative to
its own directory. Installed runtime guidance and live tool schemas own the
current API; do not load a different kernel's instructions.

- Pi package manifests, extensions, packaging and delivery:
  [pi-package-development](../../knowledge/playbooks/pi-package-development/README.md).
- Provider authentication, model catalogs and runtime behavior:
  [pi-provider-contracts](../../knowledge/playbooks/pi-provider-contracts/README.md).
- Fabric execution, tool availability, and transactional boundaries:
  [fabric-native-execution](../../knowledge/playbooks/fabric-native-execution/README.md).
- Runner/execution choice:
  [execution-router](../../knowledge/playbooks/execution-router/README.md).
- Resolve task needs against live model inventory:
  [model-resolution](../../knowledge/playbooks/model-resolution/README.md).
- Explicit Veda request: select the requested scope in
  [veda-lane](../../knowledge/playbooks/veda-lane/README.md).

The [tooling index](references/topics.md) covers specific Veda lanes, large-context
consultation and harness procedures. A planning-only request never authorizes
implementation. Do not install or configure an external planner just to answer
an ordinary planning question.

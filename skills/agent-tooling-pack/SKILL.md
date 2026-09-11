---
name: agent-tooling-pack
description: "Use when building or troubleshooting agent integrations: Pi packages and extensions, provider authentication and model catalogs, or Fabric execution surface. Ordinary planning uses engineering-pack; external model consultation uses research-pack."
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

The host chooses which model runs. This pack does not rank models or route tasks.
Do not install or configure an external planner just to answer an ordinary
planning question.

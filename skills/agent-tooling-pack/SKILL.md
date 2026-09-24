---
name: agent-tooling-pack
description: "Use when building or troubleshooting agent integrations: Pi packages and extensions, provider authentication and model catalogs, or Fabric execution surfaces, including inspecting or removing durable actors whose live tools cannot carry a capability. Also use for bounded typed judgment workflows with Jev. This pack owns agent-runtime and integration contracts; combine it with engineering for implementation or research for external evidence. Ordinary planning alone does not trigger it."
invocation: entry
---

# Agent tooling pack

These are optional tool-specific procedures, not the default engineering workflow.
Start with the narrowest matching procedure and add another only for a distinct
active integration problem. Resolve each procedure's helpers and references from
its own directory. Installed runtime guidance and live tool schemas own the
current API; do not load a different kernel's instructions.

- Pi package manifests, extensions, packaging and delivery:
  [pi-package-development](../../knowledge/playbooks/pi-package-development/README.md).
- Provider authentication, model catalogs and runtime behavior:
  [pi-provider-contracts](../../knowledge/playbooks/pi-provider-contracts/README.md).
- Fabric execution, tool availability, durable actors, and transactional
  boundaries:
  [fabric-native-execution](../../knowledge/playbooks/fabric-native-execution/README.md).
- Bounded semantic triage with a typed judge, including Jev, and portability
  between hosts:
  [typed-judgment-workflows](../../knowledge/playbooks/typed-judgment-workflows/README.md).
- Agent-team delegation, durable coordination, task learning, and workspace moves:
  [autonomous-agent-teams](../../knowledge/playbooks/autonomous-agent-teams/README.md).

The host chooses which model runs. This pack does not rank models or route tasks.
Do not install or configure an external planner just to answer an ordinary
planning question.

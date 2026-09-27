---
title: sourcebot
summary: "Use when using, configuring, administering or upgrading Sourcebot: search, indexing, code hosts, Ask/models/connectors, MCP/REST, skills, review agents, SSO/SCIM, permissions, operations and licensing."
kind: playbook
---

# Sourcebot

Sourcebot provides indexed multi-repository search, Ask, code navigation and an
MCP context server. This specialist covers the complete indexed documentation
surface through focused references, not one giant startup instruction or a copy
of every generated schema. Load only the active topic.

The [cross-repository source playbook](../cross-repo-source/README.md) remains the
owner of research applicability, corpus admission, bounded `ask_codebase` requests
and freshness proof. This specialist owns product-specific usage and operations.
It does not authorize deployment, corpus, access-policy or external-write changes.

## Choose the reference

| Task | Reference |
| --- | --- |
| Write queries, use AI Search Assist/contexts, diagnose missing results | [Search](references/search.md) |
| Connect an external agent, choose MCP tools, diagnose access | [Setup and MCP](references/setup-and-access.md) |
| Install Compose/Helm, size infrastructure or migrate v2–v5 | [Deployment and upgrades](references/deployment-and-upgrades.md) |
| Configure settings, environment, queues, Redis TLS, logs, telemetry or Analytics | [Configuration and operations](references/configuration-and-operations.md) |
| Index GitHub, GitLab, Bitbucket, Azure DevOps, Gitea, Gerrit, generic or local Git | [Connections](references/connections.md) |
| Configure login/SSO, account linking, SCIM, roles or repository ACLs | [Identity and permissions](references/identity-and-permissions.md) |
| Configure email, audit retention, licensing, trials or seats | [Administration and licensing](references/administration-and-licensing.md) |
| Configure models, Ask connectors, sharing or experimental review agents | [Ask, models and agents](references/ask-models-and-agents.md) |
| Create/import/update a skill **inside Ask Sourcebot** | [Native skills](references/native-skills.md) |
| Use REST discovery/search/source/history, scoped tokens or EE administration | [REST API](references/api.md) |
| Check documentation completeness, aliases, redirects or contradictions | [Documentation map](references/documentation-map.md) |

## Working sequence

1. Identify the task boundary, installed version, intended repository/ref and
   permitted surface. Host configuration owns endpoints, credentials and known
   plan limits. Do not infer runtime access from the documentation.
2. Read the matching reference and current schema. Distinguish UI query syntax,
   MCP arguments, REST bodies, connection config and identity-provider config.
3. Retrieve or change only what the request authorizes. For code research, use
   the canonical scoping/freshness workflow. For configuration, preserve secrets,
   existing data, repository scope and access policy.
4. Verify through the consumer: a known code hit and file read, checked Ask
   citations, allowed/denied access probes, or a task-specific integration check.
   A saved config, listed tool or healthy process is not end-to-end proof.
5. Report the version/ref, evidence and checks actually obtained, plus any
   entitlement, coverage, freshness or unresolved documentation limit.

## Non-obvious boundaries

Search defaults to the default branch; selecting a branch does not index it.
Navigation is heuristic, not compiler resolution. Self-hosting does not imply
zero egress: model providers, connectors, product telemetry and service pings are
separate data flows. Paid/custom entitlements vary by feature and release.

The [documentation map](references/documentation-map.md) accounts for all **79
indexed documentation entries plus the OpenAPI specification**, including aliases
and redirects. This is documentation coverage, not a claim that every deployment
combination was tested or that future documentation is already known. The local
skill does not automatically create or publish an Ask Sourcebot skill.

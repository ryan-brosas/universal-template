---
name: pydantic-settings-foundation
description: Use when porting layered settings/config resolution machinery — ordered settings-source pipelines, env-var field resolution with aliases, nested-delimiter explosion of complex values, .env extra harvesting, secret-dir scanning, alias-aware JSON/TOML/YAML config file sources, or argparse-style CLI settings sources with repeated-flag merging, bool flag modes, and subcommand app runtimes from pydantic-settings.
kind: foundation
invocation: manual
disable-model-invocation: true
---
# pydantic-settings: settings-source resolution foundation

## Foundation contract

This is a cold, source-specific foundation, not an operational procedure. It is
historical, revision-pinned evidence rather than timeless guidance. Current
project source, tests, requirements, and runtime behavior outrank this
projection and decide what ships.

## Provenance and revision

- Source record: `pydantic-settings`; portable upstream identity, license, coverage caveats, and retrieval history are preserved in the index.
- Recorded revision: `main@d26fc0c3944fe68cf169f86386988bb83e3df2d8`.
- Full provenance, coverage caveats, boundaries, and preserved evidence:
  `references/index.md`.

## Topic map

- Representative topics: Priority fold; Source coordination; Env name ladder;
  Complex value pipeline; Dotenv extras; Secrets scanning; File providers; CLI
  wiring.
- Scope and retrieval questions: `references/index.md#use-this-for`.
- Complete capsule chooser: `references/index.md#load-the-matching-source-dump`.
- Detailed grouped map: `references/index.md#capsule-map`.
- Source limitations and portability boundaries: `references/index.md#boundaries`.

## Retrieval

Open the index, choose one capsule matching the active question, and load only
that capsule. Revalidate its cited source and revision before relying on it. Do
not bulk-load the inventory, treat historical claims as current truth, or apply
this foundation as a procedure.

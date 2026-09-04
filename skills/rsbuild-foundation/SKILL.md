---
name: rsbuild-foundation
description: "Use when porting Rsbuild's bundler-framework kernel + built-in plugin suite + create-rsbuild scaffolder plane — instance assembly, plugin ordering, hook engine, config pipeline, CSS/asset/entry/target planes, chunk splitting, dev server + HMR socket protocol, HTML/manifest/resource-hint pipelines, stack symbolication, SSR bundle runner, template wiring + textual config-rewrite kernel, generic transform-loader registry, query-gated web workers w/ inline child-compiler builds, native-addon/WASM asset handling, env-gated diagnostics (progress/Rsdoctor/profile tracing), and the shadow-DOM browser error overlay plane."
kind: foundation
invocation: manual
disable-model-invocation: true
---
# Rsbuild: bundler-framework kernel foundation

## Foundation contract

This is a cold, source-specific foundation, not an operational procedure. It is
historical, revision-pinned evidence rather than timeless guidance. Current
project source, tests, requirements, and runtime behavior outrank this
projection and decide what ships.

## Provenance and revision

- Source record: `rsbuild`; portable upstream identity, license, coverage caveats, and retrieval history are preserved in the index.
- Recorded revision: `main@2bcf61c67072537c68f93d6700d7ac20a0f3f8f5`.
- Full provenance, coverage caveats, boundaries, and preserved evidence:
  `references/index.md`.

## Topic map

- Representative topics: Instance; Plugins; Hooks; Compiler bridge; Plugin
  API; Config; Context; Env.
- Scope and retrieval questions: `references/index.md#use-this-for`.
- Complete capsule chooser: `references/index.md#load-the-matching-source-dump`.
- Detailed grouped map: `references/index.md#capsule-map`.
- Source limitations and portability boundaries: `references/index.md#boundaries`.

## Retrieval

Open the index, choose one capsule matching the active question, and load only
that capsule. Revalidate its cited source and revision before relying on it. Do
not bulk-load the inventory, treat historical claims as current truth, or apply
this foundation as a procedure.

---
name: dsh-codex-foundation
description: "Use when porting ChatGPT-OAuth Codex provider machinery — provider-native auth adapters, single-flight browser login, cancellation and status recovery, exact-origin Web OAuth routes, CLI device-code selection, bounded Fast Mode state, quota parsing, search, image tools, Responses API policy, model-catalog settings, SSRF-guarded public HTTP loading, durable search-request session events, boot-free CLI JSON diagnostics, terminal /codex command internals (background login controller, headless-aware browser launch, redaction-bounded handler), client UI plane (slot-injected browser entry, settings OAuth lifecycle, fail-soft quota projection, fast-mode toggle, imagegen tool view), binary publication plane (sandbox-checked byte writes, atomic temp-file publish under per-path promise locks), server-side settings/Fast-Mode route gates over one bounded-body kernel, OAuth-bearer/factory/catalog adapter assembly, search config-overlay defaults, version-injection/composition-patch/release-provenance build plumbing."
kind: foundation
invocation: manual
disable-model-invocation: true
---
# dsh-codex: OpenAI Codex Subscription Provider Foundation

## Foundation contract

This is a cold, source-specific foundation, not an operational procedure. It is
historical, revision-pinned evidence rather than timeless guidance. Current
project source, tests, requirements, and runtime behavior outrank this
projection and decide what ships.

## Provenance and revision

- Source record: `dsh-codex`; portable upstream identity, license, coverage caveats, and retrieval history are preserved in the index.
- Recorded revision: `main@e3e54e206f7c829503c7e6eed378643ba0416792`.
- Full provenance, coverage caveats, boundaries, and preserved evidence:
  `references/index.md`.

## Topic map

- Representative topics: Provider auth adapter; Browser challenge lifecycle;
  Cancellation and teardown; Status recovery; Trusted request gate; Trusted
  origin store; Auth route contract; CLI auth modes.
- Scope and retrieval questions: `references/index.md#use-this-for`.
- Complete capsule chooser: `references/index.md#load-the-matching-source-dump`.
- Detailed grouped map: `references/index.md#capsule-map`.
- Source limitations and portability boundaries: `references/index.md#boundaries`.

## Retrieval

Open the index, choose one capsule matching the active question, and load only
that capsule. Revalidate its cited source and revision before relying on it. Do
not bulk-load the inventory, treat historical claims as current truth, or apply
this foundation as a procedure.

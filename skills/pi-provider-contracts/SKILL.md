---
name: pi-provider-contracts
description: "Use when building, debugging, or auditing the runtime behavior of a pi provider extension: registerProvider auth and apiKey semantics, refreshModels catalog lifecycle, before_provider_headers ordering, OpenAI SDK header merge, snapshot stores, or when real pi behaves differently from the probes claim. NOT for manifest structure, bundling, or publishing (pi-package-development)."
---

# Pi Provider Runtime Contracts

## Core Principle
Provider extensions are stitched together by ordering-sensitive contracts (auth resolution, header assembly, snapshot persistence, refresh cadence). Verify every behavior claim against the installed runtime source and a wire capture, never against a fake-harness probe or the docs in your head.

## When to Use / NOT
- **Use when:** building or debugging `registerProvider`-based providers; keyless/credential behavior; `refreshModels` lifecycle; header stripping or injection; "passes the probes, differs in real pi".
- **NOT when:** manifest structure, bundling, install, or publish (`pi-package-development`); the commit-to-merge loop (`ship-pr`).

## Workflow
1. **Map the contract from the installed runtime source, not memory.** Read in this order:
   - `pi-ai/dist/auth/resolve.js`: the stored /login credential owns the provider; the configured key (literal, `$ENV`, `!command`) is only the fallback.
   - `pi-coding-agent/dist/core/provider-composer.js`: `composeApiKeyAuth` compiles the key forms, `withConfiguredAuth` (`authHeader: true`) routes the resolved key into pi's header pipeline, and the `refreshModels` wrapper swaps the returned list via `publish({update})`.
   - `pi-coding-agent/dist/core/models-store.js`: `FileModelsStore` persists entries verbatim to `~/.pi/agent/models-store.json`, so extra scoping fields survive (they are out-of-band; version them).
   - `pi-coding-agent/dist/core/sdk.js` and the OpenAI client's `buildHeaders`: merge order is `[..., authHeaders, defaultHeaders, options.headers]` and a `null` value deletes.
2. **Respect the ordering traps** (see `references/contract-table.md` for the full table):
   - `before_provider_headers` runs before the OpenAI SDK adds `Authorization` from the resolved key. To keep a placeholder off the wire: register `authHeader: true` and null the header in the hook; a nulled `defaultHeaders` entry deletes the SDK's own auth header.
   - Never re-register the provider inside `refreshModels`: every registration fires an offline refresh, which loops. Return the list instead.
   - Online catalog refresh happens only in interactive sessions (session start, `/model`). Headless `-p` runs and `pi update --models` (bare runtime, no extensions) never fetch.
3. **Wire-verify like a hostile tester.** Stand up a recording HTTP server (method, url, authorization, body), then drive real `pi -e . --model <provider>/<id> -p` sessions in a clean `PI_CODING_AGENT_DIR` across keyless, keyed, and thinking-on variants. A fake-pi probe can pass while the real wire leaks credentials.
4. **Land it.** Every finding gets evidence (wire line or source `file:line`), a fix, an extended probe, and the repo gates; then the ship loop (see Related).

## Red Flags
- **HARD-GATE:** never declare keyless/header/auth behavior fixed from a fake-pi probe alone; capture the wire.
- **HARD-GATE:** never gate keyless fetches on apiKey presence; keyless sends no credentials.
- **HARD-GATE:** do not duplicate gateway-side routing, fallback, or credential decisions client-side; the extension stays a thin catalog + registration client.
- Honest metadata: vision/reasoning claims only for verified families; an `input: ["image"]` over-claim sends images to text-only upstreams.

## Verification
- Wire log shows the expected authorization state per scenario (keyless: header absent; keyed: real key; reasoning: `reasoning_effort` only for reasoning models with thinking on).
- Repo gates green; every fix extends a probe.

## Related
- `pi-package-development` skill: manifest, bundling, install, publish.
- `ship-pr` skill: the autonomous commit-to-merge loop used to land contract fixes.
- pi docs: `packages.md`, `extensions.md` (hook semantics), custom-provider reference.

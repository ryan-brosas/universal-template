<!-- capsule-v2 -->
# Worker persona full-access default — one frontmatter flip that re-prices the blast radius of every run

**Source:** Veda (`veda-ts`, MIT, `master@c3c69f2c340ec81ada8ea974076ce5bbaf5ccbc6`); Codebase Memory `mnt-hdd-utopia-inspo-pi-ecosystem-veda`. **Question:** What does it take — mechanically and contractually — to move an implementation worker from a workspace-write sandbox to a FULL sandbox without breaking any consumer of its resolved config?

## Frontmatter default + four-plane consistency sweep
**Path/Symbol:** `personas/worker/AGENTS.md` (frontmatter `tools: all` / `sandbox: full`); `src/agent/persona.ts:PersonaMetadata` doc (:44), `resolveAgentConfig` sandbox precedence (:249–254); `src/backend/pi.ts:toPiTools` (:76–79); `src/commands/run.ts:86–90` header; `src/commands/guide.ts` persona table (:69ff) + `src/commands/personas.ts:personaDescription`.
**Signature:** `defaultSandbox?: SandboxMode` on Persona; resolution `options.sandbox ?? personaSandbox ?? globalConfig?.defaultSandbox ?? 'read-only'`.
**Data Shape:** The flip is TWO tokens in frontmatter, but the contract ripples into four planes: the pi tool flag (full+undefined → omit `--tools`, see pi-tool-flag-tri-state), the system-prompt notice (full+undefined → SANDBOX_NOTICE_FULL, see sandbox-notice-selector), the progress header shown before the run starts, and user-facing docs.

### Decisive source
```yaml
---
tools: all
sandbox: full
---
```
```ts
// src/agent/persona.ts :249–254
// Sandbox precedence: explicit --sandbox flag, then persona frontmatter
// sandbox:, then the config DEFAULT_SANDBOX, then read-only.
const sandbox = options.sandbox
  ?? personaSandbox
  ?? globalConfig?.defaultSandbox
  ?? 'read-only';
```

**Flow:** frontmatter parsed by parsePersonaMetadata (`parseSandboxMode` validates the scalar; unknown values are DROPPED silently, leaving defaultSandbox undefined rather than erroring) → precedence ladder resolves `full` for the worker unless the operator overrides with `--sandbox` → downstream planes derive from the RESOLVED pair. The test suite was rewritten in the same commit: fixture frontmatter flipped, `expect(persona.defaultSandbox).toBe('full')`, and `resolveAgentConfig(worker)` now asserts `config.systemPrompt` contains `'full access'` and not `'no access to tools'` (:472).
**Invariant:** A default-sandbox change is a SECURITY-BEARING default, not a preference: every surface that displays or consumes blast radius must change in the SAME commit (header text "its header must display the sandbox mode ... before the run starts — the blast-radius change is visible up front", run.ts :86–90 comment). Also note the precedence test inversion this drift caused: with persona=full, a global `defaultSandbox: 'workspace-write'` can no longer override it — persona beats global config; only the explicit flag does.
**Probe:** `grep -c "defaultSandbox).toBe('full')" tests/agent/persona.test.ts` → 2; `sed -n '1,3p' personas/worker/AGENTS.md | tail -2` shows `tools: all` / `sandbox: full`; `tests/agent/persona.test.ts:472` pins `'full access'` in the resolved prompt.
**Count check:** `grep -n 'options.sandbox' src/agent/persona.ts` → exactly :251.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pi-ecosystem-veda", query: "resolveAgentConfig sandbox precedence defaultSandbox persona", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the pattern: capability defaults belong in persona frontmatter, resolve through a fixed precedence ladder, and force a same-commit sweep of flag-wiring, notice-selection, header, and docs. Adapt which planes exist in your host (you may have fewer). Omit veda's specific personas. Coverage caveat: pinned by the rewritten worker-defaults suite at this commit.

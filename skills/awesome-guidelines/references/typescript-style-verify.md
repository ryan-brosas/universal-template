<!-- capsule-v2 -->
# Verification — does TS style hold in CI and review?

**Source:** Google tsguide enforcement; basarat styleguide tooling. **Question:** Can an agent prove module/type/class rules on changed paths?

## Tooling seam
**Path/Symbol:** project `tsconfig.json`, ESLint, formatter.
**Signature:** `tsc --noEmit`, `@typescript-eslint/*`, Prettier if configured.
**Data Shape:** exit code 0 on changed `.ts`/`.tsx` files.

### Probe checklist
| Rule cluster | Command / rule | Capsule |
|---|---|---|
| No default exports | grep / `import/no-default-export` | modules-imports |
| No `any` | `@typescript-eslint/no-explicit-any` | types-nullability |
| Import type hygiene | `verbatimModuleSyntax` or `importsNotUsedAsValues` | modules-imports |
| No non-null assertion | `@typescript-eslint/no-non-null-assertion` | classes-api |
| Mutable exports | `import/no-mutable-exports` | modules-imports |
| Unified overloads | `@typescript-eslint/unified-signatures` | types-nullability |

**Flow:** run formatter → `tsc --noEmit` → eslint on changed paths → manual capsule checklist on review.
**Invariant:** style probes run on **source** `.ts`/`.tsx`, not emitted JS.
**Probe:** all commands exit 0; P0 skill-validator clean after skill wiring.

## Review seam (human or agent)
- [ ] Named exports; no namespace/require
- [ ] `import type` for type-only symbols
- [ ] No nullable exported type aliases
- [ ] Callbacks use `void` when return ignored
- [ ] Catch bindings `unknown`
- [ ] No `#private` / `const enum` without documented exception
- [ ] Domain boundaries still checked via `typescript-coding-standards` when modeling untrusted input

## Verdict
Mechanical gates plus capsule checklist complete TypeScript style ingest. Learning note: `typescript-style-learning-note.md`.

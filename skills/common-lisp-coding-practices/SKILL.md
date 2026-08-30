---
name: common-lisp-coding-practices
description: "Use when authoring or reviewing Common Lisp — lisp-case naming, *earmuffs*/+constants+, SLIME indentation, :import-from packages, CLOS typed slots, defgeneric protocols, and ASDF test in CI."
disable-model-invocation: true
---

# Common Lisp Coding Practices

Application skill for Common Lisp style learning (from the archived `awesome-guidelines` style capsules). For Emacs Lisp, use `emacs-lisp-coding-practices` when ingested.

## Core Principle

Common Lisp quality is **idiomatic names + explicit packages + documented CLOS** — small libraries, exported APIs only, SLIME-consistent layout.

## When to Use / NOT

- Common Lisp libraries, ASDF systems, SBCL/CCL deployments.
- Setting up SLIME indent, SBCL warnings, ASDF test-op in CI.

**NOT when:**

- Clojure/Scheme/Racket — use language-specific practice skills.
- Generated system stubs only — validate generator.

## Workflow

1. **Format & files** — indent, columns, headers (`lisp-style-formatting-files.md`).
2. **Naming** — lisp-case, *, +, predicates (`lisp-style-naming-symbols.md`).
3. **Packages** — defpackage, ASDF (`lisp-style-packages-systems.md`).
4. **CLOS & control** — classes, when/unless (`lisp-style-clos-control.md`).
5. **Verify** — load/test system; SBCL `(declaim (optimize ...))` policy; review exports.

## Red Flags

- camelCase or snake_case symbols
- `:use` heavy packages (beyond `:cl`)
- `other-package::internal` in production
- Missing docstrings on exported API
- `slot-value` in application logic
- Unrelated generic function overloads
- Commented-out code blocks
- Monolithic system with no library boundaries
- Abbreviated symbol names

## Verification

- `asdf:test-system` / project test script
- SBCL compile with project warning policy
- SLIME/common-lisp-indent style check
- Capsule checklist on package export list

## Skill Result Contract

```xml
<skill_result>
  <skill>common-lisp-coding-practices</skill>
  <status>success|partial|blocked|failure</status>
  <artifacts>lisp diff, asdf test output</artifacts>
  <evidence>learning note + capsule probes cited</evidence>
  <risks>package leak, CLOS protocol drift, or none</risks>
</skill_result>
```

## References

- `awesome-guidelines/references/lisp-style-learning-note.md`
- `awesome-guidelines/references/lisp-style-formatting-files.md`
- `awesome-guidelines/references/lisp-style-naming-symbols.md`
- `awesome-guidelines/references/lisp-style-packages-systems.md`
- `awesome-guidelines/references/lisp-style-clos-control.md`

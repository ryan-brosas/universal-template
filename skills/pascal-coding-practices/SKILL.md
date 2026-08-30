---
name: pascal-coding-practices
description: "Use when authoring or reviewing Free Pascal/GNU Pascal — 2-space/no-tab layout, lowercase keywords, PascalCase T/P types, unit block order, brace comments, result returns, and fpc -Wall or fpsonar in CI."
disable-model-invocation: true
---

# Pascal Coding Practices

Application skill for classic Pascal style learning (from the archived `awesome-guidelines` style capsules). For Lazarus/LCL or Delphi VCL/Object Pascal, use `delphi-coding-practices` instead.

## Core Principle

Pascal library quality is **dialect-picked layout + ordered units** — declare FPC-tight or GPC-spaced style once, mirror interface in implementation, compile warning-clean.

## When to Use / NOT

- FPC compiler/RTL patches, GNU Pascal (GPC) code, portable `.pas` libraries without Delphi RTL.
- Setting up `fpc -Wall`, fpsonar, or project compile checks in CI.

**NOT when:**

- Lazarus LCL components or Delphi IDE projects — use `delphi-coding-practices`.
- Generated `.pas` — validate generators.

## Workflow

1. **Layout** — indent, begin/end, spacing profile (`pascal-style-formatting-layout.md`).
2. **Naming** — keywords, T/P types (`pascal-style-naming-types.md`).
3. **Units** — files, order, uses (`pascal-style-units-structure.md`).
4. **Comments/control** — braces, flow, CI (`pascal-style-comments-control.md`).
5. **Verify** — `fpc -Wall`, fpsonar optional, tests on changed units.

## Red Flags

- Tab indentation
- UPPERCASE keywords
- Mixed FPC-tight and GPC-spaced styles in one project
- `if x then begin` on one line
- Spaces around operators in FPC compiler tree
- Missing space before `(` in GPC published calls
- `(* *)` or `//` comments in published GPC code
- Function assigns to its name instead of `result` (FPC)
- Implicit Result variable against GPC rules
- Multiple units per `.pas` file
- Uppercase filenames
- Missing license/header block (GPC)
- Interface/implementation declaration order mismatch
- Unit cycles in interface uses
- Empty unit `begin end.`
- Wrong case semicolon in `case` before `else`
- Undocumented interface exports (GPC)
- Macros for constants
- goto/Exit for ordinary control flow
- `for` counter mutation or post-loop reliance
- Commenting out code with `{ … }` instead of `{$if False}`
- Comments inside compiler directives
- FCL-style non-indented routines in FPC compiler tree (or reverse)

## Verification

- `fpc -Wall` (and project `-O3` if GPC baseline) on changed units
- fpsonar or house linter (NoTabs, LowercaseKeywords, BeginEndRequired)
- Uses-cycle and interface-order review on new units
- Capsule checklist on spacing profile declaration in AGENTS/project docs

## Skill Result Contract

```xml
<skill_result>
  <skill>pascal-coding-practices</skill>
  <status>success|partial|blocked|failure</status>
  <artifacts>pas diff, fpc/fpsonar output</artifacts>
  <evidence>learning note + capsule probes cited</evidence>
  <risks>spacing drift, unit cycle, undefined loop behavior, or none</risks>
</skill_result>
```

## References

- `awesome-guidelines/references/pascal-style-learning-note.md`
- `awesome-guidelines/references/pascal-style-formatting-layout.md`
- `awesome-guidelines/references/pascal-style-naming-types.md`
- `awesome-guidelines/references/pascal-style-units-structure.md`
- `awesome-guidelines/references/pascal-style-comments-control.md`

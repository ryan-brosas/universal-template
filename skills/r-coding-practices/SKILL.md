---
name: r-coding-practices
description: "Use when authoring or reviewing R — tidyverse snake_case/<-/2-space layout, native |> pipes, roxygen2 docs, Google BigCamelCase/return/:: deltas when declared, and styler/lintr/testthat in CI."
disable-model-invocation: true
---

# R Coding Practices

Application skill for R style learning (`awesome-guidelines` deep ingest). Default to tidyverse + styler/lintr; when project declares Google R guide, apply BigCamelCase functions, explicit `return()`, and `pkg::fun()` qualification.

## Core Principle

R analysis quality is **consistent formatting + pipe-clear data flow** — `<-` and snake_case objects, native `|>`, documented exports, mechanical styler/lintr gates.

## When to Use / NOT

- R scripts, R packages, Quarto/Rmd analysis repos, Shiny apps.
- Setting up styler, lintr, testthat, R CMD check in CI.

**NOT when:**

- Renviron/secrets — never commit credentials.
- Generated `.Rd`/NAMESPACE-only churn — validate hand-edited `.R`.

## Workflow

1. **Syntax** — spacing, braces, `<-` (`r-style-formatting-syntax.md`).
2. **Naming/files** — snake_case vs BigCamelCase policy (`r-style-naming-files.md`).
3. **Functions/pipes** — `|>`, returns, control (`r-style-functions-pipes.md`).
4. **Docs/verify** — roxygen, styler, lintr (`r-style-docs-verify.md`).
5. **Verify** — styler, lintr, tests on changed files.

## Red Flags

- `=` assignment
- `T`/`F` instead of TRUE/FALSE
- Tabs or inconsistent indent vs 2-space styler profile
- Misaligned closing brace
- Dots in function names (non-S3)
- Mixed tidyverse snake and Google Camel function names
- `%>%` in new code without magrittr feature need
- Right-hand pipe `->` (Google forbid)
- Implicit return in Google-baseline functions
- Missing explicit `return()` in Google-baseline functions
- Unqualified external functions in Google codebase
- Blanket `@import` package (Google)
- `attach()`
- Semicolons or multiple statements per line
- Single-line braced `if`/`else` bodies (except expression form)
- `if (length(x))` without explicit comparison
- `&`/`|` inside scalar `if`
- Same-line `if (x) return(x)`
- Partial argument matching
- Assignment inside function call
- Overlong unbroken pipes/calls
- `~` lambdas instead of `\()` for new short anonymous functions
- Spaces inside `{{ embracing }}`
- Shadowing `c`, `mean`, `data`
- `final`/`final2` filenames
- Libraries scattered mid-file
- Undocumented `@export`
- Missing `pkg::` qualification (Google)
- No styler/lintr in CI for team projects

## Verification

- `styler::style_file()` or `style_pkg()` on changed paths
- `lintr::lint()` with project `.lintr` config
- `devtools::test()` / `R CMD check` for packages
- Roxygen coverage on new exports
- Capsule checklist on declared baseline (tidyverse vs Google)

## Skill Result Contract

```xml
<skill_result>
  <skill>r-coding-practices</skill>
  <status>success|partial|blocked|failure</status>
  <artifacts>R diff, styler/lintr/test output</artifacts>
  <evidence>learning note + capsule probes cited</evidence>
  <risks>baseline drift, namespace collision, pipe unreadability, or none</risks>
</skill_result>
```

## References

- `awesome-guidelines/references/r-style-learning-note.md`
- `awesome-guidelines/references/r-style-formatting-syntax.md`
- `awesome-guidelines/references/r-style-naming-files.md`
- `awesome-guidelines/references/r-style-functions-pipes.md`
- `awesome-guidelines/references/r-style-docs-verify.md`

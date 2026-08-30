<!-- capsule-v2 -->
# Formatting and syntax — is assignment and brace structure mechanical?

**Source:** Tidyverse §Syntax/Braced expressions/Assignment. **Question:** Would styler and a reader agree on `<-`, spacing, and `}` alignment?

## Syntax seam
**Path/Symbol:** `.R`/`.Rmd` scripts and package sources.
**Signature:** `<-` assignment; 2-space indent; aligned closing braces.
**Data Shape:** 80-column wrapped calls.

### Decisive pattern
```r
fit_model <- function(data, response, predictors) {
  if (nrow(data) == 0) {
    stop("Empty data", call. = FALSE)
  }

  model <- lm(
    reformulate(predictors, response = response),
    data = data,
    na.action = na.omit
  )

  model
}
```

**Flow:** assign with `<-` not `=` → indent braced bodies 2 spaces → `{` last token on line; `}` first token on its own line aligned with `if`/`function` → space after commas; no space before `(` in ordinary calls; space before `(` in `if`/`for`/`while`/`function (` → space around infix operators except high-precedence (`::`, `$`, `^`, `:`, unary `-`) → use `"` for strings; `TRUE`/`FALSE` not `T`/`F` → no semicolons → break calls >80 cols one argument per line → loop/`if` bodies always braced except allowed single-line `if` expression form.
**Invariant:** `=` assignment, cuddled misaligned `}`, or `T`/`F` literals fail tidyverse review.
**Probe:** `styler::style_file()`; lintr assignment/TRUE_FALSE lints.

## Vertical space seam
**Flow:** blank lines separate thoughts; no leading/trailing empty lines inside functions; single blank between functions or pipe blocks.
**Invariant:** double-spacing inside tiny helpers fails readability review.
**Probe:** visual chunk review on changed functions.

## Verdict
`<-`, two-space braced blocks, spaced infix, 80-col wraps. Learning note: `r-style-learning-note.md`.

<!-- capsule-v2 -->
# Functions and pipes — is data flow one object wide and control explicit?

**Source:** Tidyverse §Functions/Pipes/Control flow; Google §Pipes/Returns. **Question:** Do pipes stay readable and returns match project baseline?

## Pipe seam
**Path/Symbol:** dplyr/tidyverse pipelines and function bodies.
**Signature:** native `|>`; newline after pipe; early returns braced.
**Data Shape:** `data |> step() |> step()` with 2-space step indent.

### Decisive pattern
```r
iris_summary <-
  iris |>
  filter(Species == "setosa") |>
  summarise(
    mean_width = mean(Sepal.Width, na.rm = TRUE),
    .by = Species
  )

find_abs <- function(x) {
  if (x > 0) {
    return(x)
  }
  x * -1
}
```

**Flow:** prefer base `|>` over `%>%` in new code → space before `|`>; newline after; indent continued steps 2 spaces → use pipes for sequential steps on one primary object; extract named intermediates when multiple objects or long inline sub-pipes → assign with `result <- data |> …` (Google: never `… -> result`) → tidyverse: implicit final expression return; use explicit `return()` only for early exit in its own `{}` block → Google: always `return()` → short anonymous `\ (x) mean(x)`; multi-line use `function(x) {` → control modifiers (`return`, `stop`, `break`, `next`) each in braced block → scalar conditions use `&&`/`||`; avoid `if (length(x))` coercion → never `attach()`.
**Invariant:** void multi-object pipe soup, same-line `if (x) return(x)`, or Google code with implicit return fails review.
**Probe:** pipe layout spot check; return-style audit against project baseline.

## Args seam
**Flow:** name non-obvious args (`na.rm = TRUE`); no partial matching; no assignment inside calls except capture side-effects pattern.
**Invariant:** `mean(x = 1:10, , FALSE)`-style calls fail review.
**Probe:** named-argument review on changed function calls.

## Verdict
Indented native pipes, braced control, baseline-correct returns. Learning note: `r-style-learning-note.md`.

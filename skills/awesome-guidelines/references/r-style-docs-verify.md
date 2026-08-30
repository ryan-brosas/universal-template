<!-- capsule-v2 -->
# Documentation and verification — are exports documented and style enforced?

**Source:** Tidyverse §Documentation; Google §Qualifying namespaces. **Question:** Can lintr/styler run clean on changed R sources?

## Documentation seam
**Path/Symbol:** exported functions and package metadata.
**Signature:** roxygen2 markdown; `@param` sentences; qualified namespaces (Google).
**Data Shape:** `#' Title sentence` + `@return`/`@examples`.

### Decisive pattern
```r
#' Compute mean petal width by species
#'
#' @param data Data frame containing `Petal.Width` and grouping columns.
#' @param group Bare column name to group by.
#' @return A tibble of summary statistics.
#' @export
summarise_width <- function(data, group) {
  data |>
    dplyr::summarise(
      mean_width = mean(Petal.Width, na.rm = TRUE),
      .by = {{ group }}
    )
}
```

**Flow:** document exports with roxygen2 (markdown enabled) → title sentence case without trailing period → `@param`/`@return` complete sentences → internal helpers `@noRd` → cross-link with `[fun()]`/`[pkg::fun()]` → Google code: qualify external calls `pkg::fun()`; prefer `@importFrom pkg fun` at use site over blanket `@import` → package-level doc in `packagename-package.R`.
**Invariant:** undocumented export, bare `@import` in Google tree, or missing namespace qualification fails review.
**Probe:** `devtools::document()`; roxygen coverage on `@export`.

## Verify seam
**Flow:** run `styler::style_file()` / `style_pkg()` on changed paths → run `lintr` with project config → run `testthat`/CI R CMD check tests on packages.
**Invariant:** committed formatting drift or lintr errors without noqa rationale fails CI.
**Probe:** styler diff; `lintr::lint_dir()` exit status.

## Verdict
Roxygen exports, qualified deps when required, styler + lintr in CI. Learning note: `r-style-learning-note.md`.

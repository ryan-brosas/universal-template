<!-- capsule-v2 -->
# Naming and files — are identifiers and paths project-consistent?

**Source:** Tidyverse §Object names/Files; Google §Naming. **Question:** Does the tree declare tidyverse snake_case or Google BigCamelCase for functions?

## Naming seam
**Path/Symbol:** functions, variables, filenames.
**Signature:** snake_case objects (both guides); verb functions; baseline-specific function case.
**Data Shape:** `fit_model()` or `FitModel()` per project policy.

### Decisive pattern
```r
# Tidyverse baseline
compute_mean_width <- function(data) {
  mean(data$Sepal.Width, na.rm = TRUE)
}

# Google baseline
ComputeMeanWidth <- function(data) {
  return(mean(data$Sepal.Width, na.rm = TRUE))
}

.DoComputePrivately <- function(x) {
  return(x)
}
```

**Flow:** variables nouns in snake_case (`day_one`, `n_users`) → functions verbs (`add_row`, `FitModel` per baseline) → no dots in function names (reserve for S3) → avoid shadowing `c`, `mean`, `data`, `T` → filenames lowercase with `-`/`_`, `.R` extension, descriptive not `temp.r` → order related scripts with zero-padded prefixes or ISO dates → libraries loaded once at file top with `# ----` section headers.
**Invariant:** mixed function naming conventions, uppercase-only filename differences, or `final_report.R` naming fails review.
**Probe:** lintr object_name_linter; filename grep; project baseline doc check.

## File seam
**Flow:** one concise purpose per file; machine-readable names (no spaces/symbols).
**Invariant:** space-containing paths or undifferentiated `utils.R` soup fails organization review.
**Probe:** file inventory on new scripts.

## Verdict
Consistent snake_case data + declared function case; readable lowercase files. Learning note: `r-style-learning-note.md`.

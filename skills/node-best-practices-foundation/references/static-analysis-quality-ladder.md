<!-- capsule-v2 -->
# Static-analysis quality ladder — which tool class owns which defect class?

**Source:** nodebestpractices CC-BY-SA-4.0 `master@dc3d60c2`; Codebase Memory `nodebestpractices`. **Question:** What does ESLint+Prettier cover vs what needs cross-file static analysis, and how does CI enforce it?

## ESLint=single-file correctness/style, Prettier=auto-formatting (compose via config packages), Sonar-class=multi-file smells gating CI red/green
**Path/Symbol:** `sections/codestylepractices/eslint_prettier.md` (:4-6 division of labor, :24 integration packages), `sections/testingandquality/refactoring.md` (:7 smell classes, :7 CI-gate mechanics, lint-complement sentence).
**Signature:** compose via `prettier-eslint` / `eslint-plugin-prettier` / `eslint-config-prettier`; static-analysis tools (Sonar, Code Climate) FAIL THE BUILD on detected smells and notify the author.
**Data Shape:** two defect planes — intra-file (max-len warnings vs auto-format) and inter-file (duplicated code, long methods, long parameter lists, complexity).

### Decisive source
```text
# refactoring.md :7 — the complement split + CI gate
Most linting tools will focus on code styles like indentation and missing
semicolons... while static analysis tools will focus on finding code smells
(duplicate code, complexity analysis, etc.) that are in single files and
multiple files. If your CI integrates with a tool like Sonar or Code Climate,
the build will fail if it detects code smells and inform the author on how
to address the issue.
```

**Flow:** Prettier formats automatically (ESLint would only warn too-wide, eslint_prettier :4-6) → composition packages stop the tools fighting → static analysis runs IN CI as a build-blocking quality gate feeding the refactor loop.
**Invariant:** the ladder is ordered by blast radius: formatting (auto-fixed) < style/correctness lint (warned) < structural smells (build-breaking). Refactoring is treated as an iterative process driven by detectors, not big-bang rewrites. Same "convert practice into a gate" doctrine as `static-require-discipline`.
**Probe:** no runner upstream. Deterministic probe: `grep -c 'eslint-config-prettier' sections/codestylepractices/eslint_prettier.md` >= 1 && `grep -c 'Code Climate' sections/testingandquality/refactoring.md` >= 1 && `grep -c 'code smells' sections/testingandquality/refactoring.md` >= 2.
**Retrieve:** `await mcp.codebase_memory.search_code({ project: "nodebestpractices", pattern: "prettier-eslint", limit: 5 });`

## Verdict
Adopt the three-tier ladder and the build-blocking static-analysis gate. Adapt tool names to current equivalents (Biome-type combined toolers: keep the separation of concerns). Omit dead links.

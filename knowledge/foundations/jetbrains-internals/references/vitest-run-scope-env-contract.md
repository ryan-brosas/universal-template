<!-- capsule-v2 -->
# Vitest run-scope env contract — how does the IDE tell a helper which SUBSET of tests is running, and what must the adapter suppress in each scope?

**Source:** JetBrains IDE installed build `WebStorm 262.9437.145` (vitest-intellij + jest-intellij helpers); Codebase Memory `jetbrains-webstorm`. **Question:** Running one test vs one file vs everything changes what should be reported — where does scope knowledge come from and how do the adapters branch on it?

## _JETBRAINS_* environment plane
**Path/Symbol:** `plugins/javascript-plugin/helpers/vitest-intellij/vitest-intellij-util.js:319-335` (`getRunScopeType` cached read of `_JETBRAINS_VITEST_RUN_SCOPE_TYPE`; `isSuitesOrTestsScope()` = suite|test|selected_tests; `isSingleTestFileScope()` = test_file|suite|test); connector `shouldIgnoreSkippedTask` (:319-321, skip-mode tasks ignored only under suites/tests scope) and root-rename gate `getOrCreateFileNode` (:151-161, single-test-file scope renames ROOT via updateRootNode but NOT for workspaces — "they can rerun file more than once"); jest twin `_JETBRAINS_TEST_RUNNER_RUN_SCOPE_TYPE` (jest-intellij-util.js:237-248) with pending-drop under suitesOrTests (:111-113); node:test twin `_JETBRAINS_TEST_NAME_PATTERN_FILTRATION` (test-tree-builder.js:19-26, pass events with skip==='test name does not match pattern' pop the start stack silently).
**Signature:** module-level consts; all reads lazily cached into module globals.
**Data Shape:** sibling env knobs on the same plane: `_JETBRAINS_VITEST_RUN_WITH_COVERAGE`, `_JETBRAINS_VITEST_IS_NG_CLI_CONTEXT`, `_JETBRAINS_BASE_TEST_REPORTER_ABSOLUTE_PATH`, `_JETBRAINS_INTELLIJ_RUN_WITH_COVERAGE` (jest), `_JB_INTELLIJ_JASMINE_REPORTER_DISABLED`, plus socket trio JB_TEAMCITY_SOCKET_{PATH,PORT,HOST} and personas JB_VERBOSE / JB_VITEST_LOG_TEST_FAILURE_DETAILS.

### Decisive source
```js
// vitest-intellij-util.js
function isSuitesOrTestsScope() {
  const runScopeType = getRunScopeType();
  return runScopeType === 'suite' || runScopeType === 'test' || runScopeType === 'selected_tests';
}
function isSingleTestFileScope() {
  const runScopeType = getRunScopeType();
  return runScopeType === 'test_file' || runScopeType === 'suite' || runScopeType === 'test';
}
// connector — workspace guard on root rename
if (vitestIntellijUtil.isSingleTestFileScope()
  && !isWorkspace) {                       // Don't update the root node for workspaces…
  tree.updateRootNode(fileNodeName, path.relative('', path.dirname(testFilePath)),
    'file://' + testFilePath);
  fileNode = tree.root;
}
```

**Flow:** IDE launches the runner process with scope env set → adapters read ONCE (cached global) → single-test-file mode collapses the tree INTO the renamed root (title shows file+dir comment+location) → suites/test/selected modes drop skipped/pending non-matches so the tree contains only requested tests → coverage flags ride the same plane to push lcov config back via `sendMessage('vitest-coverage-config'|'jest-coverage-config')`.
**Invariant:** scope values OVERLAP (suite/test satisfy both predicates) and the two branches are consumed at DIFFERENT decision points — suppression uses isSuitesOrTestsScope, root-collapse uses isSingleTestFileScope. Wrong port: collapsing the root for workspaces (reruns would rename repeatedly), or dropping pending results in full runs (legitimate skips vanish).
**Probe:** deterministic source pins: all six `_JETBRAINS_*` names grep-verified verbatim across helpers (env-plane census in work record); behavior battery pins the shared Tree/root-rename primitives these gates drive.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-webstorm", query: "getRunScopeType isSuitesOrTestsScope", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt an explicit scope-env contract between launcher and reporter instead of inferring scope from events. Adapt value vocabulary to your runner. Omit coverage messaging if not porting IDE coverage.

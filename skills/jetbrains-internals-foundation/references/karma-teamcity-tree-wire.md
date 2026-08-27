<!-- capsule-v2 -->
# Karma TeamCity tree wire (nodeId/parentNodeId) - how does a server-side reporter stream a test tree the IDE can render and navigate?

**Source:** PhpStorm installed build PS-262.9437.196 (lib/intellijReporter.js 302L, lib/tree.js 275L, lib/karma-browser-tracker.js); Codebase Memory project jetbrains-phpstorm. **Question:** What message contract turns browser test events into an IDE tree with navigation, logs, and diff data?

## The extended TeamCity dialect
**Path/Symbol:** tree.js:89-115 (getStartMessage/getFinishMessage with nodeId/parentNodeId/nodeType/locationHint), :223-272 (setStatus status map + extra finish params), intellijReporter.js:112-114 via intellijUtil (##intellij-event control lines), :64-113 (clearOtherAdapters/clearBrokenReporters WEB-73511), :115-141 (LogManager postpone/attach), :244-292 (normalizeAssertionError), karma-browser-tracker.js:7-61 (browsers_change diffing).
**Data Shape:** control channel ##intellij-event[type:JSON] lines (configFile snapshot, browserConnected/browserDisconnected{id,name,isAutoCaptured}, browserCapturingFailed). Tree channel ##teamcity[enteredTheMatrix | testSuiteStarted/testSuiteFinished | testStarted/testFinished|testIgnored|testFailed] with numeric nodeId + parentNodeId (position-independent nesting), nodeType config|browser|suite|test, locationHint '<nodeType>://<dotted.path>', finish extras duration/error=yes/message/details/expected/actual, plus testStdOut nodeId=... for logs.

### Decisive source
```js
text += " nodeId='" + this.id;
text += "' parentNodeId='" + (this.parentNode ? this.parentNode.id : 0);
text += "' nodeType='" + this.type;
text += "' locationHint='" + intellijUtil.attributeValueEscape(this.type + '://' + this.locationHint);
// finish command by status: 0 testFinished / 1 testIgnored / 2,3 testFailed (+ error='yes' on 3)
```

**Flow:** per runStart a fresh Tree roots at id=1 named basename(karma.conf.js) (cwd fallback id=0 never emits a start), enteredTheMatrix is written on nextTick; browsers are children keyed by browser.ID, suites dedup by NAME key, specs always fresh; recursive finishIfStarted closes open branches at runComplete; Jasmine__TopLevel__Suite filtered from suite paths; skipped-and-not-pending specs unreported entirely. Reporter output MONOPOLIZED: other reporters adapters evicted from the MultiReporter so no line can double or prefix teamcity frames (restored if eviction empties - the intellij reporter itself is an adapter), Angular-20 broken undefined-adapter entries filtered first. Browser logs are postponed (newline-joined) and flushed as ONE testStdOut onto the spec node; orphans flush raw at runComplete. Assertion normalization strips the leading message (and compound Name-colon-message) off the stack head and splits expected/actual from result.assertionErrors[0]. isAutoCaptured heuristic: launchId present or all-digit connection id means auto-captured.
**Invariant:** TWO escaping regimes coexist deliberately: attribute values use the pipe dialect (n r x l p || ' [ ]) while locationHint dotted paths use joinList backslash-escaping of delimiter and backslash only. The SAME joinList kernel exists in this install in mocha-intellijUtil.js:73-106 and base-test-reporter/intellij-util.js:21-54 (MCP cross-package search evidence) - it is a shared platform convention, not local color.
**Probe:** node --check green across the reporter family this run; MCP get_code_snippet pinned sendIntellijEvent to intellijUtil.js:112-114 (4 callers). Event-vocabulary census executed against shell plane separately (see terminal capsule).
**Coverage caveat:** no shipped tests; behavior derived from shipped code.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-phpstorm", query: "sendIntellijEvent attributeValueEscape joinList", limit: 8 });
```

## Verdict
Adopt numeric nodeId/parentNodeId over name-nesting whenever trees can contain duplicate names (browsers, parametrized suites). Adapt node types to your domain. Omit adapter eviction if you are the ONLY reporter - but keep it if users can configure reporters in their own configs.

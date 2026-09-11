<!-- capsule-v2 -->
# TeamCity service-message grammar (`##teamcity[...]`) — what exact wire format does an IDE test reporter emit, and which characters must be escaped?

**Source:** JetBrains IDE installed build `WebStorm 262.9437.145`, byte-identical (md5 `3131eff6…`) across pycharm/rider/rustrover/clion/rubymine/phpstorm*; Codebase Memory `jetbrains-webstorm`. **Question:** If I port the IDE-side of a test runner integration, what message vocabulary and escaping rules must my emitter satisfy so the IDE parses every line?

## The command/attribute grammar
**Path/Symbol:** `plugins/nodeJS/js/mocha-intellij/lib/mochaIntellijUtil.js:escapeAttributeValue` (:47-64) + `doEscapeCharCode` mapping table (:6-35); `mochaIntellijTree.js:getInitMessage` (:148-168), `getStartMessage` (:194-209), `getFinishMessage` (:251-262), `getExtraFinishMessageParameters` (:536-563).
**Signature:** `escapeAttributeValue(str: string): string`; message shape `'##teamcity[' + command + ' key=\'' + escapeAttributeValue(value) + '\'']'`.
**Data Shape:** commands = `enteredTheMatrix`, `testCount count='N'`, `testingStarted`, `testingFinished`, `testSuiteStarted/testSuiteFinished`, `testStarted/testFinished|testIgnored|testFailed`, `testStdErr out='…'`. Attributes: `nodeId`, `parentNodeId`, `name`, `running`, `nodeType`, `locationHint` (= `<nodeType>://<locationPath>`), `metainfo`, plus finish extras `duration`, `error='yes'`, `message`, `details`, `expected`, `actual`, `expectedFile`, `actualFile`.

### Decisive source
```js
addMapping('\n', 'n');   addMapping('\r', 'r');
addMapping('\u0085', 'x'); addMapping('\u2028', 'l'); addMapping('\u2029', 'p');
addMapping('|', '|');    addMapping('\'', '\'');
addMapping('[', '[');    addMapping(']', ']');
// escapeAttributeValue: fast path returns str unchanged when no special char present
res += '|'; res += escaped;   // pipe-prefixed escapes
```

**Flow:** emitter writes one `##teamcity[command …]` per line → IDE parses attributes by scanning for `key='…'` spans → any raw `|`, `'`, `[`, `]`, or Unicode newline inside a value would terminate/splice the span, hence the pipe-escape.
**Invariant:** every attribute value passes through `escapeAttributeValue`; the fast-path scan means clean strings are emitted byte-identical. Wrong port: HTML-style `&amp;` escaping or JSON quoting — TeamCity messages use ONLY this pipe dialect. Note `joinList` (locationPath builder) uses a SEPARATE backslash escape for delimiter chars — two escaping regimes in one file.
**Probe:** executed live via node v26.7.0 battery `/tmp/jb-p7/probe-v3.js`: `escapeAttributeValue('\n|\'') === '|n|||\''`, `escapeAttributeValue('\u2028') === '|l'`, clean-string fast path unchanged, `joinList(['a.b','c'],0,2,'.') === 'a\\.b.c'`.
**Coverage caveat:** no upstream test suite ships in the install; probes are behavior-derived from the shipped code itself.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-webstorm", query: "escapeAttributeValue", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the command vocabulary and pipe-escaping verbatim for ANY IDE test-reporter port (it is the contract, not an implementation detail). Adapt command sets to your host's supported subset. Omit mocha-specific attribute choices.

<!-- capsule-v2 -->
# Test-node state machine (CREATED→REGISTERED→STARTED→FINISHED) — how does the tree keep the IDE's test view consistent without double-finish races?

**Source:** JetBrains IDE installed build `WebStorm 262.9437.145`; Codebase Memory `jetbrains-webstorm`. **Question:** What lifecycle must every reported test/suite node obey, and which states may legally re-emit or must throw?

## The four-state Node kernel
**Path/Symbol:** `plugins/javascript-plugin/helpers/base-test-reporter/intellij-tree.js` — `NodeState.CREATED/REGISTERED/STARTED/FINISHED` (:143-146), `Node.prototype.register` (:153-157), `start` (:212-223), `finish(finishParentIfLast)` (:260-276), `TestSuiteNode.prototype.onChildFinished` (:480-487). The mocha-intellij variant (`plugins/nodeJS/js/mocha-intellij/lib/mochaIntellijTree.js`) is the same machine minus idPrefix/metainfo.
**Signature:** `start(): void`, `finish(finishParentIfLast?: boolean): void`, `register(): void`.
**Data Shape:** state transitions emit exactly one message each: CREATED --register--> REGISTERED (init msg `running='false'`); CREATED|REGISTERED --start--> STARTED (init `running='true'` or short re-start `nodeId+name+running='true'` — the comment pins it as "required for BaseTestMessage.getTestName"); REGISTERED|STARTED --finish--> FINISHED.

### Decisive source
```js
Node.prototype.start = function () {
  if (this.state === NodeState.FINISHED) { throw Error("Cannot start finished node"); }
  if (this.state === NodeState.STARTED) { return; }   // idempotent re-start
  …
};
Node.prototype.finish = function (finishParentIfLast) {
  if (this.tree.root === this) { return; }            // base variant: root finish is INERT
  if (this.state !== NodeState.REGISTERED && this.state !== NodeState.STARTED) {
    throw Error('Unexpected node state: ' + this.state);
  }
  …
  if (finishParentIfLast) { parent.onChildFinished(); }
};
TestSuiteNode.prototype.onChildFinished = function() {
  this.finishedChildCount++;
  if (this.finishedChildCount === this.children.length && this.state !== NodeState.FINISHED) {
    this.finish(true);   // cascading suite close when LAST child finishes
  }
};
```

**Flow:** pre-registration at run start (`register()` → non-spinning IDE icons) → late `start()` flips to spinning → outcome set → `finish` emits terminal command → optional cascade closes parent suites bottom-up.
**Invariant:** a node finishes AT MOST once (second finish throws on state guard); starting a FINISHED node throws; re-starting a STARTED node is silently idempotent; suite auto-close fires only when finished-child count equals children length AND the suite itself isn't already FINISHED. Wrong port: emitting `testFinished` twice (IDE drops/duplicates results) or finishing suites eagerly before their last child.
**Probe:** executed live via node v26.7.0 battery `/tmp/jb-p7/probe-v3.js`: second `setOutcome` throws; `root.finish(true)` inert in base variant; duplicate-name children collapse `findChildNodeByName` into an array with suite preference while `findChildNodesByName` returns both; `idPrefix` prefixes generated ids (`'fp-1'` → `'fp-1-4'`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-webstorm", query: "onChildFinished NodeState", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the four-state machine and one-message-per-transition discipline for any structured test reporting. Adapt the idPrefix scheme (only multi-runner hosts need it). Omit the legacy `util.inherits` prototype plumbing.

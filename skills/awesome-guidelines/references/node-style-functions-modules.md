<!-- capsule-v2 -->
# Functions and modules — are functions small with requires at top and safe module boundaries?

**Source:** felixge/node-style-guide §Functions, §Miscellaneous; Microsoft getting-started. **Question:** Do callbacks, requires, and prototype rules follow Node community hygiene?

## Function seam
**Path/Symbol:** Node modules, event handlers, async callbacks.
**Signature:** ~15 lines; early return; named closures; requires at file top.
**Data Shape:** no nested closure pyramids; no native prototype extension.

### Decisive pattern
```js
const http = require('http');

req.on('end', function onEnd() {
  finishRequest();
});

function finishRequest() {
  if (!session) {
    return;
  }
  // ...
}
```

**Flow:** keep functions **short** (~15 lines target) → **return early** to avoid deep nesting → **name** non-trivial callbacks (`function onEnd()`) for stack traces → **avoid nested closures** — extract sibling functions → method **chain**: one call per line, indent continuation → put all **require/import at top** so dependencies are visible → **never extend** built-in prototypes (`Array.prototype.foo = …`) → avoid `eval`, `with`, exotic `Object.freeze` tricks in app code → avoid **setters**; getters OK when side-effect free → prefer **local npm packages** and `package.json` scripts over global `-g` CLI installs when versions matter.
**Invariant:** nested anonymous callback pyramid, mid-file require, or native prototype extension fails Node module hygiene review.
**Probe:** require/import position scan; grep `\.prototype\.`; nesting depth review on changed handlers.

## Platform seam
**Flow:** read `PORT` from `process.env.PORT || default` for servers → track dependencies in `package.json`; `.gitignore` `node_modules` → restore with `npm install` not committed tree.
**Invariant:** hard-coded port only with documented reason; committed node_modules in app repo fails packaging review.
**Probe:** grep `listen(` for env PORT; gitignore check.

## Verdict
Short early-return functions, named callbacks, top requires, no prototype hacks, env PORT + package.json hygiene. Learning note: `node-style-learning-note.md`.

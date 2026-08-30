<!-- capsule-v2 -->
# Cucumber event-envelope duck-typing ladder — how do you support pre-event-API cucumber versions without branching your whole reporter?

**Source:** JetBrains IDE installed build `WebStorm 262.9437.145` (proprietary distribution; study/reference use only); Codebase Memory `jetbrains-webstorm`. **Question:** above.

## Capability sniff + accessor duality
**Path/Symbol:** `plugins/javascript-cucumber/lib/cucumberjs_formatter_common.js`:`getFeature/getScenario/getStep/getStepResult` (:209-235) plus accessors `getStatus/getLine/getName/getUri` (:193-207).
**Signature:** `getFeature(eventOrFeature)` → payload item or the object itself; accessors `obj.getX ? obj.getX() : obj.x`.
**Data Shape:** old cucumber (≤v1) delivers EVENT WRAPPERS exposing only `getPayloadItem(key)`; new versions deliver the domain objects directly. The discriminator is `getUri == null && getPayloadItem != null` — a wrapper has no URI of its own but CAN yield payloads.

### Decisive source
```js
function getFeature(eventOrFeature) {
  if (eventOrFeature.getUri == null && eventOrFeature.getPayloadItem != null) {
    return eventOrFeature.getPayloadItem('feature')
  }
  return eventOrFeature
}
function getName(obj) {
  return escape(obj.getName? obj.getName(): obj.name);   // method-form (v1+) vs property-form
}
```

**Flow:** every handler first normalizes its argument through the matching unwrap helper, then reads fields through the four accessors, so handler bodies never mention a cucumber version.
**Invariant:** unwrap is keyed on CAPABILITY SHAPE, not on a stored version number — the same binary handles both shapes in one run; `getName` escapes at read time so no message site can forget escaping.
**Probe:** executed live against the REAL module: an old-style envelope `{getUri:null, getPayloadItem:k=>k==='step'?step:null}` driven through `BeforeStep` produced the identical `testStarted` message as the modern direct-object form; a malformed event lacking BOTH shapes failed LOUD with `TypeError: Cannot read properties of undefined` at :202 (fail-fast, not silent skip).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "jetbrains-webstorm", qualified_name: "jetbrains-webstorm.plugins.javascript-cucumber.lib.cucumberjs_formatter_common.buildHandlers" });
// full closure body :55-246 returned byte-equal to the on-disk source
```

## Verdict
Adopt capability-shape sniffing over version tables when absorbing a dependency whose API split is "wrapper vs direct object" — it survives intermediate/unknown versions. Adapt the specific discriminator to your dependency's marker methods. Omit nothing; note the deliberate asymmetry that `getStepResult` discriminates on `getFailureException == null` (a different marker than the other three) because step results carry failure data the wrappers lack.

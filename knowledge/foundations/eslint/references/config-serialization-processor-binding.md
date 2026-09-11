<!-- capsule-v2 -->
# Config serialization plane — how does a runtime Config project back to JSON without leaking plugin objects or functions?

**Source:** ESLint MIT `main@c27bc926e496985eb7911c09eb60914b2e4b5d0f`; Codebase Memory project `eslint`. **Question:** How do live language/processor/plugin bindings survive JSON.stringify-style projection, and what must be refused?

## Private identity fields + refusing toJSON
**Path/Symbol:** `lib/config/config.js` #languageName/#processorName (:438–444), processor branch (:518–549), `toJSON` (:563–591), `languageOptionsToJSON` (:367–401), `assertNotFunction` (:346–357), `getObjectId` (:307–336).
**Signature:** `toJSON(): Record<string, any>`; `languageOptionsToJSON(options, objectKey)`; `getObjectId(obj): string|null` (name or "name@version" from obj or obj.meta).
**Data Shape:** constructor keeps the ORIGINAL STRING ids for language/processor in private fields while storing the RESOLVED OBJECTS on the instance; plugins serialize to ["ns:name@version"] (bare namespace when no meta).

### Decisive source
```js
// processor binding — string id resolves through the plugin map, id is retained:
if (typeof processor === "string") {
  const { pluginName, objectName } = splitPluginIdentifier(processor);
  this.#processorName = processor;                    // keep the STRING
  this.processor = plugins[pluginName].processors[objectName];  // store the OBJECT
} else if (typeof processor === "object") {
  this.#processorName = getObjectId(processor);       // meta.name[@version] identity
  this.processor = processor;
}
toJSON() {
  if (this.processor && !this.#processorName) throw new Error(
    "Could not serialize processor object (missing 'meta' object).");
  return { ...this,
    plugins: Object.entries(this.plugins).map(([namespace, p]) =>
      getObjectId(p) ? namespace + ":" + getObjectId(p) : namespace),
    language: this.#languageName,
    languageOptions: languageOptionsToJSON(this.languageOptions),
    processor: this.#processorName };
}
// refusal ladder: functions anywhere under languageOptions throw —
// 'Cannot serialize key "syntax" in "languageOptions": Function values are not supported.'
// (also thrown for a toJSON() RESULT that is a function; messageTemplate config-serialize-function)
```

**Flow:** walk languageOptions top-down; a value with callable toJSON() converts and STOPS descending (children never see their own toJSON called after a parent converted); objects with name+method identity collapse to "name@version"; anything else recurses; every leaf passes assertNotFunction.
**Invariant:** the private *Name fields are the only serialization source of truth — projecting `{...this}` directly would embed parser/processor FUNCTIONS. Missing identity (object processor without meta) is a hard throw at toJSON time, not silent data loss. A toJSON() returning a function is itself rejected, closing the re-entrancy hole.
**Probe:** `tests/lib/config/config.js` (:530–659 full projection incl. parser→"testParser", :648+ parent-toJSON-stops-descending, :788–818 function refusals incl. toJSON-result case, :821–848 missing-meta processor throw). Executed at pin: --grep 'toJSON|validateRulesConfig' → 31 passing.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "eslint", query: "Config toJSON languageOptionsToJSON assertNotFunction getObjectId processor", limit: 10 });
await mcp.codebase_memory.get_code_snippet({ project: "eslint", qualified_name: "eslint.lib.config.config.Config.constructor" });
```

## Verdict
Adopt dual-track binding (resolved object on the instance, original string id in a private field) plus the function-refusing, parent-short-circuiting JSON walk for any runtime config that must hash/log cleanly. Adapt identity grammar (name@version) to host metadata conventions; omit the plugins-array projection if hosts have no plugin namespaces.

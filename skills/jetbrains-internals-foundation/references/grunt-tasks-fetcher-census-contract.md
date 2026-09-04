<!-- capsule-v2 -->
# Grunt tasks fetcher census contract - how do you inventory a user's buildfile without a build-tool API?

**Source:** PhpStorm Light installed build PS-262.9421 (proprietary; cite-only); Codebase Memory `jetbrains-phpstorm-light`. **Question:** How can an IDE enumerate a project's grunt tasks (including aliases and multi-targets) by running the user's own Gruntfile?

## javascript-plugin helpers/buildTools/grunt/tasks/grunt-tasks-fetcher.js
**Path/Symbol:** `plugins/javascript-plugin/helpers/buildTools/grunt/tasks/grunt-tasks-fetcher.js` — module.exports registers hidden task `_intellij_grunt_tasks_fetcher` (:3, :9); census over `grunt.task._tasks` + `grunt.config.getRaw()` (:10-11); alias detection `isAliasTask` (:72-74); dependency parse `getDependencies` (:76-86); inline port of grunt's `isValidMultiTaskTarget` (:41-48); output `writeToStdOut = console.log` (:88-90).
**Signature:** one JSON line on stdout: `{aliasTasks: [{name, info, filePath?, dependencies[]}], coreTasks: [{name, info, filePath?, multi?, targets[]}]}`.
**Data Shape:** alias identity lives in grunt's HUMAN info string: `'Alias for "a", "b".'` — parsed by prefix `'Alias for "'` (:5) + `lastIndexOf('"')` + `split('", "')`.

### Decisive source
```js
grunt.registerTask('_intellij_grunt_tasks_fetcher', 'Prints grunt task structure', function () {
  var rawTasks = grunt.config.getRaw();
  var _tasks   = grunt.task._tasks;
  ...
  if (_task != null && isString(_task.name) && _task.name !== GRUNT_TASK_STRUCTURE_FETCHER_TASK_NAME) { // self-exclude
    ...
    if (isAliasTask(_task)) { ijTask.dependencies = getDependencies(_task); aliasTasks.push(ijTask); }
    else {
      ijTask.targets = [];
      // Multi task targets can't start with _ or be a reserved property (options).
      // Logic from grunt/lib/grunt/task.js (isValidMultiTaskTarget)
      if (prop !== 'options' && prop.indexOf('_') !== 0) {
        var target = rawTask[prop];
        if (isObject(target) || Array.isArray(target)) ijTask.targets.push(prop);
      }
    }
  }
});
function getDependencies(task) {           // parse grunt's own display text
  var endInd = task.info.lastIndexOf('"');
  return task.info.substring(ALIAS_TASK_PREFIX.length, endInd).split('", "');
}
```

**Flow:** The IDE runs the user's Gruntfile with this module preloaded; the registered hidden task walks grunt's internal `_tasks` registry, classifies each entry as alias vs core, extracts per-task metadata (`task.meta.filepath`, `multi === true`), computes multi-task targets from raw config while replicating grunt's own validity rule inline, self-excludes by name compare, and emits exactly ONE console.log line for the parent to JSON.parse.
**Invariant:** no grunt API beyond `registerTask/config.getRaw/task._tasks/meta`; when upstream has no stable interface, parse its display strings but guard them (`endInd <= 0 ⇒ []`); the fetcher must be invisible to the census it produces.
**Probe:** EXECUTED against the shipped file with a stub grunt object (node v26.7.0): transcript `coreTasks: [{"name":"build","info":"Build it","filePath":"/x/gruntfile.js","targets":["src"]}]` — `options` and `_hidden` filtered, non-object target excluded, fetcher absent from its own census; `aliasTasks: [{"name":"ngtask","dependencies":["build","test"]}]` — two-dependency alias parsed from info text.
**Coverage caveat:** coverage no_recorded_issue @ gen 2026-08-24T13:57:05Z; no dedicated upstream test exists.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-phpstorm-light", query: "grunt tasks fetcher alias census", limit: 6 });
```

## Verdict
Adopt the inject-hidden-census-task pattern to inventory any convention-driven task runner (gulp, make wrappers) through the tool's own runtime. Adapt the classification source — prefer real APIs wherever they exist, fall back to guarded display-string parsing. Omit multi-target replication only when your runner exposes target lists structurally.

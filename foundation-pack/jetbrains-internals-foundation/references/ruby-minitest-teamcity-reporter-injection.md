<!-- capsule-v2 -->
# Ruby minitest TeamCity reporter injection — how does an IDE get structured results out of a test framework that owns its own output?

**Source:** JetBrains installed distribution (proprietary install; helper files carry Apache-2.0 headers) RubyMine Linux `dist@262.9437.192`; Codebase Memory `jetbrains-rubymine`. **Question:** How does RubyMine inject a structured-output reporter into minitest without forking it, and what does the runner entrypoint contract look like?

## Minitest plugin-convention injection + shipped runner entrypoint
**Path/Symbol:** `plugins/ruby/rb/testing/runner/minitest_runner.rb` (whole file, 17L); `plugins/ruby/rb/testing/patch/testunit/minitest/rm_reporter_plugin.rb:21` (`Minitest.plugin_rm_reporter_init`), :111 (`RubyMineReporter < Reporter`). Graph: search_graph name_pattern ".*rm_(load_minitest|reporter_plugin).*" resolves both modules line-exactly.
**Signature:** `Minitest.plugin_rm_reporter_init(options)` → clears + installs; `RubyMineReporter.new(options = {})`; runner reads `ENV["INTELLIJ_IDEA_RUN_CONF_TEST_FILE_PATH"]` ("||"-separated).
**Data Shape:** env-carried run config (no argv protocol); reporters array replaced in place; per-class→per-test nested hashes with Set defaults track pending tests/suites.

### Decisive source
```ruby
# rm_load_minitest.rb — must load BEFORE Minitest::Test exists (prepend on ruby<=2.7)
begin
  require 'minitest'
rescue LoadError
  return
end
Minitest.load_plugins

# rm_reporter_plugin.rb :21
def plugin_rm_reporter_init(options)
  assert_no_minitest_reporters          # raises if Minitest::Reporters@@loaded — hard conflict guard
  Minitest.reporter.reporters.clear     # replace, do not append
  Minitest.reporter.reporters << Minitest::RubyMineReporter.new(options)
end

# minitest_runner.rb :6
files = ENV["INTELLIJ_IDEA_RUN_CONF_TEST_FILE_PATH"] # separated by "||" filenames
raise Exception.new("A test file must be provided") if files.nil? || files.length == 0
require 'minitest/rm_load_minitest'   # before user files, see prepend note :11-12
files.split("||").each { |file| require file }
```

**Flow:** IDE sets env → ruby runs minitest_runner.rb → settings + patch load path seeded → rm_load_minitest loads minitest and triggers plugin discovery → minitest calls plugin_rm_reporter_init by naming convention → all third-party reporters cleared, RubyMineReporter installed → user test files required → prerecord/record drive suite-tree service messages.
**Invariant:** The injection rides minitest's OWN plugin hook (`plugin_<name>_init`), never monkey-patches the run loop; conflicting `Minitest::Reporters.use!` must fail loudly (error text tells users to gate on `ENV['RM_INFO']`); location identity is `file://<path>:<line>` with `ruby_minitest_qn://<fqn>` fallback when source_location is unavailable.
**Probe:** Executed under system ruby 3.4.10 (no minitest gem → end-to-end run BLOCKED, recorded not faked): module/entry contract verified by whole-file read + graph resolution + coverage check (all three files no_recorded_issue); message emission proven live by the ruby-teamcity-message-factory probe.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-rubymine", name_pattern: ".*rm_(load_minitest|reporter_plugin).*", limit: 10 });
await mcp.codebase_memory.search_graph({ project: "jetbrains-rubymine", query: "teamcity test formatter reporter minitest", limit: 12 });
```

## Verdict
Adopt: inject via the framework's native plugin/discovery hook, clear-and-install (not append), conflict-guard competing reporter libraries with an actionable error, carry run configuration in namespaced env vars. Adapt: superclass-set nesting walk (MINITEST_SUPERCLASSES enumerates Rails TestCase classes) — recompute for your host's frameworks. Omit: the separate-loader workaround once your ruby floor is >=3.0 (in-file comment says merge it back).
